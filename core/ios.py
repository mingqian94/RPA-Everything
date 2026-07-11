"""iPhone semi-automation through pymobiledevice3.

This module deliberately exposes only the capabilities that are practical
without a signed WDA/XCUITest runner: device discovery, developer readiness,
clipboard copy, app launch, screenshots, and diagnostics.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class IosError(RuntimeError):
    pass


_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_hidden(cmd: list[str], **kwargs):
    if _CREATE_NO_WINDOW:
        kwargs.setdefault("creationflags", _CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)


def _pmd3_cmd(explicit: str | None = None) -> list[str]:
    configured = explicit or os.environ.get("RPA_IOS_PYMOBILEDEVICE3_PATH")
    if configured:
        return [configured]
    return [sys.executable, "-m", "pymobiledevice3"]


def _run(args: list[str], timeout: float = 30, udid: str | None = None, pmd3: str | None = None) -> str:
    env = os.environ.copy()
    if udid:
        env["PYMOBILEDEVICE3_UDID"] = udid
    proc = _run_hidden(
        [*_pmd3_cmd(pmd3), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise IosError(out.strip() or f"pymobiledevice3 failed: {' '.join(args)}")
    return out


def pmd3_available(pmd3: str | None = None) -> bool:
    try:
        proc = _run_hidden(
            [*_pmd3_cmd(pmd3), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False


@dataclass
class IosDeviceInfo:
    udid: str
    name: str = "iPhone"
    model: str = "iPhone"
    version: str = ""
    connection: str = "USB"
    host: str = ""


@dataclass
class IosDiagnosticResult:
    name: str
    ok: bool
    detail: str = ""


def _fix_ios_name(value: str | None) -> str:
    if not value:
        return "iPhone"
    for enc in ("latin1", "cp1252"):
        try:
            fixed = value.encode(enc).decode("gbk")
            if fixed and fixed != value:
                return fixed
        except Exception:
            pass
    return value


def _tcp_open(host: str, port: int, timeout: float = 0.8) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def _arp_hosts() -> list[str]:
    hosts: list[str] = []
    try:
        proc = _run_hidden(["arp", "-a"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        text = proc.stdout.decode("utf-8", "replace")
    except Exception:
        return hosts
    for match in re.finditer(r"\b((?:192\.168|10|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+)\b", text):
        ip = match.group(1)
        if ip.endswith(".1") or ip.endswith(".255") or ip in hosts:
            continue
        hosts.append(ip)
    return hosts


def list_usb_devices(pmd3: str | None = None) -> list[IosDeviceInfo]:
    if not pmd3_available(pmd3):
        return []
    try:
        raw = _run(["usbmux", "list"], timeout=20, pmd3=pmd3)
        devices = json.loads(raw)
    except Exception:
        return []

    result: list[IosDeviceInfo] = []
    for item in devices:
        if item.get("DeviceClass") != "iPhone":
            continue
        udid = item.get("UniqueDeviceID") or item.get("Identifier")
        if not udid:
            continue
        result.append(IosDeviceInfo(
            udid=udid,
            name=item.get("DeviceName") or "iPhone",
            model=item.get("ProductType") or "iPhone",
            version=item.get("ProductVersion") or "",
            connection="USB",
        ))
    return result


async def _wifi_devices(timeout: float) -> list[IosDeviceInfo]:
    from pymobiledevice3.bonjour import browse_remotepairing
    from pymobiledevice3.lockdown import create_using_tcp

    candidate_hosts: list[str] = []
    seen_hosts: set[str] = set()
    for answer in await browse_remotepairing(timeout=timeout):
        for address in answer.addresses:
            host = address.full_ip
            if not host or ":" in host or "%" in host or host in seen_hosts:
                continue
            seen_hosts.add(host)
            candidate_hosts.append(host)

    manual_hosts = [h.strip() for h in os.environ.get("RPA_IOS_WIFI_HOSTS", "").split(",") if h.strip()]
    for host in [*manual_hosts, *_arp_hosts()]:
        if host not in seen_hosts and _tcp_open(host, 62078):
            seen_hosts.add(host)
            candidate_hosts.append(host)

    devices: list[IosDeviceInfo] = []
    for host in candidate_hosts:
        try:
            lockdown = await asyncio.wait_for(create_using_tcp(host, autopair=False), timeout=4)
            try:
                info = lockdown.short_info
                devices.append(IosDeviceInfo(
                    udid=info.get("UniqueDeviceID") or f"wifi:{host}",
                    name=_fix_ios_name(info.get("DeviceName")) or "iPhone",
                    model=info.get("ProductType") or "iPhone",
                    version=info.get("ProductVersion") or "",
                    connection="WiFi",
                    host=host,
                ))
            finally:
                await lockdown.close()
        except Exception:
            continue
    return devices


def list_wifi_devices(timeout: float = 3.0) -> list[IosDeviceInfo]:
    if not pmd3_available():
        return []
    try:
        return asyncio.run(_wifi_devices(timeout))
    except Exception:
        return []


def list_devices(include_wifi: bool = False) -> list[IosDeviceInfo]:
    devices = list_usb_devices()
    if include_wifi:
        seen = {(d.connection, d.udid, d.host) for d in devices}
        for device in list_wifi_devices():
            key = (device.connection, device.udid, device.host)
            if key not in seen:
                devices.append(device)
                seen.add(key)
    return devices


def first_device(include_wifi: bool = False) -> str:
    devices = list_devices(include_wifi=include_wifi)
    if not devices:
        raise IosError(
            "No iPhone found. Install pymobiledevice3, connect/trust the iPhone, "
            "and enable Developer Mode for semi-automation."
        )
    return devices[0].udid


class IosDevice:
    def __init__(self, udid: str | None = None, pmd3: str | None = None):
        self.pmd3 = pmd3
        self.udid = udid or first_device()

    def ensure_developer_ready(self) -> None:
        status = _run(["amfi", "developer-mode-status"], timeout=20, udid=self.udid, pmd3=self.pmd3).strip().lower()
        if "true" not in status:
            raise IosError("iPhone Developer Mode is not enabled.")
        _run(["mounter", "auto-mount"], timeout=60, udid=self.udid, pmd3=self.pmd3)

    def copy_text(self, text: str) -> None:
        if not text:
            return
        _run(["developer", "core-device", "copy", "--userspace", text], timeout=20, udid=self.udid, pmd3=self.pmd3)

    def launch_app(self, bundle_id: str) -> None:
        _run(
            ["developer", "core-device", "launch-application", "--userspace", bundle_id, "noop"],
            timeout=30,
            udid=self.udid,
            pmd3=self.pmd3,
        )

    def screenshot_to(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        _run(
            ["developer", "core-device", "screen-capture", "screenshot", "--userspace", str(out)],
            timeout=30,
            udid=self.udid,
            pmd3=self.pmd3,
        )
        return out


def run_diagnostics(udid: str | None = None, include_clipboard_check: bool = False) -> list[IosDiagnosticResult]:
    results: list[IosDiagnosticResult] = []
    if not pmd3_available():
        return [IosDiagnosticResult("pymobiledevice3", False, "Install with: pip install pymobiledevice3")]
    try:
        dev = IosDevice(udid=udid)
        results.append(IosDiagnosticResult("iphone_connection", True, dev.udid))
    except Exception as e:
        return [IosDiagnosticResult("iphone_connection", False, str(e))]

    try:
        dev.ensure_developer_ready()
        results.append(IosDiagnosticResult("developer_ready", True, "Developer Mode and image mount OK"))
    except Exception as e:
        results.append(IosDiagnosticResult("developer_ready", False, str(e)))

    if include_clipboard_check:
        try:
            dev.copy_text("RPA-Everything iPhone diagnostics")
            results.append(IosDiagnosticResult("clipboard", True, "copied diagnostic text"))
        except Exception as e:
            results.append(IosDiagnosticResult("clipboard", False, str(e)))

    return results
