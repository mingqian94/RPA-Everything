"""Android automation through ADB.

This module is intentionally business-neutral. It exposes the same primitives
that an operator would use when driving a real Android device from a PC:
device discovery, screenshots, taps, swipes, key events, file transfer, and
basic diagnostics.
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from core.config import get as _cfg_get


class AdbError(RuntimeError):
    pass


class InjectPermissionError(AdbError):
    """Android rejected synthetic input events."""


def adb_path(explicit: str | None = None) -> str:
    """Resolve the adb executable path.

    Priority:
    1. explicit argument
    2. config.yaml: android.adb_path
    3. env var: ANDROID_ADB_PATH, via config.get fallback
    4. adb on PATH
    """
    configured = explicit or _cfg_get("android.adb_path")
    if configured:
        return str(Path(configured).expanduser())
    found = shutil.which("adb")
    if found:
        return found
    raise AdbError(
        "adb was not found. Set android.adb_path in config.yaml or add adb to PATH."
    )


def _run_global(args: list[str], adb: str | None = None, timeout: float = 20) -> tuple[str, str, int]:
    cmd = [adb_path(adb), *args]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return (
        proc.stdout.decode("utf-8", "replace"),
        proc.stderr.decode("utf-8", "replace"),
        proc.returncode,
    )


@dataclass
class AndroidDeviceInfo:
    serial: str
    state: str
    model: str = ""
    product: str = ""


@dataclass
class AndroidUiNode:
    text: str = ""
    resource_id: str = ""
    content_desc: str = ""
    class_name: str = ""
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
    clickable: bool = False

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)


def _parse_bounds(raw: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", raw or "")
    if not match:
        return (0, 0, 0, 0)
    return tuple(int(part) for part in match.groups())


def _parse_ui_xml(xml: str) -> list[AndroidUiNode]:
    root = ET.fromstring(xml)
    nodes: list[AndroidUiNode] = []
    for el in root.iter("node"):
        attrs = el.attrib
        nodes.append(AndroidUiNode(
            text=attrs.get("text", ""),
            resource_id=attrs.get("resource-id", ""),
            content_desc=attrs.get("content-desc", ""),
            class_name=attrs.get("class", ""),
            bounds=_parse_bounds(attrs.get("bounds", "")),
            clickable=attrs.get("clickable") == "true",
        ))
    return nodes


def _node_matches(value: str, target: str, exact: bool) -> bool:
    if exact:
        return value == target
    return target in value


def list_devices(adb: str | None = None, include_offline: bool = False) -> list[AndroidDeviceInfo]:
    """Return devices reported by `adb devices -l`.

    Wireless debugging may expose the same physical phone twice via an mDNS
    alias ending with `_adb-tls-connect._tcp`; those entries are filtered out.
    """
    out, err, code = _run_global(["devices", "-l"], adb=adb)
    if code != 0:
        raise AdbError(err or out)

    devices: list[AndroidDeviceInfo] = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        if "_adb-tls-connect._tcp" in serial:
            continue
        if state != "device" and not include_offline:
            continue
        props = {}
        for token in parts[2:]:
            if ":" in token:
                k, v = token.split(":", 1)
                props[k] = v
        devices.append(AndroidDeviceInfo(
            serial=serial,
            state=state,
            model=props.get("model", ""),
            product=props.get("product", ""),
        ))
    return devices


def first_device(adb: str | None = None) -> str:
    devices = list_devices(adb=adb)
    if not devices:
        raise AdbError("No online Android device found.")
    return devices[0].serial


class AndroidDevice:
    def __init__(self, serial: str | None = None, adb: str | None = None):
        self.adb = adb_path(adb)
        self.serial = serial or first_device(self.adb)
        self._resolution: tuple[int, int] | None = None

    def _run(self, args: list[str], binary: bool = False, timeout: float = 30):
        cmd = [self.adb, "-s", self.serial, *args]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if binary:
            if proc.returncode != 0:
                err = proc.stderr.decode("utf-8", "replace")
                raise AdbError(err or f"adb command failed: {' '.join(args)}")
            return proc.stdout
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        if proc.returncode != 0:
            raise AdbError(err or out)
        return out

    def shell(self, command: str, timeout: float = 30) -> str:
        out = self._run(["shell", command], timeout=timeout)
        if "SecurityException" in out and "INJECT_EVENTS" in out:
            raise InjectPermissionError(
                "Synthetic input was blocked. On MIUI/HyperOS, enable USB debugging "
                "(Security settings), reboot the phone, and reconnect ADB."
            )
        return out

    def connect(self) -> bool:
        out, _, _ = _run_global(["connect", self.serial], adb=self.adb)
        return "connected" in out.lower() or "already" in out.lower()

    def is_online(self) -> bool:
        return any(d.serial == self.serial and d.state == "device" for d in list_devices(self.adb, True))

    def ensure_online(self) -> None:
        if self.is_online():
            return
        if ":" in self.serial:
            self.connect()
            time.sleep(0.5)
        if not self.is_online():
            raise AdbError(f"Device is not online: {self.serial}")

    def resolution(self) -> tuple[int, int]:
        if self._resolution is None:
            out = self.shell("wm size")
            match = re.search(r"(\d+)x(\d+)", out)
            if not match:
                raise AdbError(f"Unable to parse Android resolution from: {out!r}")
            self._resolution = (int(match.group(1)), int(match.group(2)))
        return self._resolution

    def screencap(self) -> bytes:
        self.ensure_online()
        data = self._run(["exec-out", "screencap", "-p"], binary=True, timeout=20)
        if data.startswith(b"\x89PNG"):
            return data

        # Fallback for devices/adb versions that mangle exec-out screencap.
        remote = "/sdcard/_rpa_everything_screencap.png"
        self.shell(f"screencap -p {remote}", timeout=20)
        data = self._run(["exec-out", "cat", remote], binary=True, timeout=20)
        self.shell(f"rm -f {remote}", timeout=10)
        if not data.startswith(b"\x89PNG"):
            raise AdbError("ADB screencap did not return a valid PNG.")
        return data

    def screencap_to(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(self.screencap())
        return out

    def tap(self, x: int, y: int) -> None:
        self.shell(f"input tap {int(x)} {int(y)}")

    def tap_ratio(self, rx: float, ry: float) -> None:
        if not (0 <= rx <= 1 and 0 <= ry <= 1):
            raise ValueError("rx and ry must be between 0 and 1.")
        w, h = self.resolution()
        self.tap(round(w * rx), round(h * ry))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        self.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")

    def swipe_ratio(self, rx1: float, ry1: float, rx2: float, ry2: float, duration_ms: int = 300) -> None:
        w, h = self.resolution()
        self.swipe(round(w * rx1), round(h * ry1), round(w * rx2), round(h * ry2), duration_ms)

    def key(self, keycode: str) -> None:
        self.shell(f"input keyevent {keycode}")

    def dump_ui_xml(self) -> str:
        remote = "/sdcard/window_dump.xml"
        self.shell(f"uiautomator dump {remote}", timeout=20)
        xml = self.shell(f"cat {remote}", timeout=20)
        self.shell(f"rm -f {remote}", timeout=10)
        if "<hierarchy" not in xml:
            raise AdbError(f"Unable to dump Android UI XML: {xml[:200]}")
        return xml

    def ui_nodes(self) -> list[AndroidUiNode]:
        return _parse_ui_xml(self.dump_ui_xml())

    def find_ui_node(
        self,
        text: str = "",
        resource_id: str = "",
        content_desc: str = "",
        exact: bool = False,
    ) -> AndroidUiNode | None:
        for node in self.ui_nodes():
            if text and not _node_matches(node.text, text, exact):
                continue
            if resource_id and not _node_matches(node.resource_id, resource_id, exact):
                continue
            if content_desc and not _node_matches(node.content_desc, content_desc, exact):
                continue
            return node
        return None

    def tap_ui_node(
        self,
        text: str = "",
        resource_id: str = "",
        content_desc: str = "",
        exact: bool = False,
    ) -> AndroidUiNode:
        node = self.find_ui_node(text=text, resource_id=resource_id, content_desc=content_desc, exact=exact)
        if node is None:
            raise AdbError("No Android UI node matched the requested selector.")
        x, y = node.center
        self.tap(x, y)
        return node

    def adbkeyboard_installed(self) -> bool:
        out = self.shell("pm list packages com.android.adbkeyboard", timeout=10)
        return "com.android.adbkeyboard" in out

    def current_ime(self) -> str:
        return self.shell("settings get secure default_input_method", timeout=10).strip()

    def set_ime(self, ime: str) -> None:
        self.shell(f"ime enable {ime}", timeout=10)
        self.shell(f"ime set {ime}", timeout=10)

    def input_text(self, text: str, unicode: bool = False, restore_ime: bool = True) -> None:
        if unicode:
            adb_ime = "com.android.adbkeyboard/.AdbIME"
            if not self.adbkeyboard_installed():
                raise AdbError(
                    "ADBKeyboard is required for unicode Android input. "
                    "Install com.android.adbkeyboard or call input_text(..., unicode=False)."
                )
            previous_ime = self.current_ime()
            self.set_ime(adb_ime)
            payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
            try:
                self.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {payload}")
            finally:
                if restore_ime and previous_ime and previous_ime != "null":
                    try:
                        self.set_ime(previous_ime)
                    except Exception:
                        pass
            return
        escaped = text.replace("%", "%25").replace(" ", "%s").replace("&", r"\&")
        self.shell(f"input text {escaped}")

    def push(self, local: str | Path, remote: str) -> None:
        local_path = Path(local)
        if not local_path.exists():
            raise FileNotFoundError(str(local_path))
        self._run(["push", str(local_path), remote], timeout=120)

    def media_scan(self, remote_file: str) -> None:
        self.shell(
            "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
            f"-d file://{remote_file}"
        )


@dataclass
class DiagnosticResult:
    name: str
    ok: bool
    detail: str = ""


def run_diagnostics(serial: str | None = None, adb: str | None = None, include_input_check: bool = False) -> list[DiagnosticResult]:
    """Run non-destructive checks by default.

    Set include_input_check=True to send HOME as a safe-ish input test.
    """
    results: list[DiagnosticResult] = []
    try:
        dev = AndroidDevice(serial=serial, adb=adb)
        dev.ensure_online()
        results.append(DiagnosticResult("adb_connection", True, dev.serial))
    except Exception as e:
        return [DiagnosticResult("adb_connection", False, str(e))]

    try:
        w, h = dev.resolution()
        results.append(DiagnosticResult("resolution", True, f"{w}x{h}"))
    except Exception as e:
        results.append(DiagnosticResult("resolution", False, str(e)))

    try:
        png = dev.screencap()
        results.append(DiagnosticResult("screenshot", png.startswith(b"\x89PNG"), f"{len(png)} bytes"))
    except Exception as e:
        results.append(DiagnosticResult("screenshot", False, str(e)))

    try:
        nodes = dev.ui_nodes()
        results.append(DiagnosticResult("uiautomator", True, f"{len(nodes)} nodes"))
    except Exception as e:
        results.append(DiagnosticResult("uiautomator", False, str(e)))

    try:
        ok = dev.adbkeyboard_installed()
        detail = "installed" if ok else "not installed"
        results.append(DiagnosticResult("adbkeyboard", ok, detail))
    except Exception as e:
        results.append(DiagnosticResult("adbkeyboard", False, str(e)))

    if include_input_check:
        try:
            dev.key("KEYCODE_HOME")
            results.append(DiagnosticResult("input", True, "sent KEYCODE_HOME"))
        except Exception as e:
            results.append(DiagnosticResult("input", False, str(e)))

    return results
