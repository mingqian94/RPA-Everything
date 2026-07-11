import json

import pytest

from core import ios


class FakeProc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.mark.unit
def test_list_usb_devices_parses_iphones(monkeypatch):
    payload = json.dumps([
        {
            "DeviceClass": "iPhone",
            "UniqueDeviceID": "udid-1",
            "DeviceName": "Ray iPhone",
            "ProductType": "iPhone14,2",
            "ProductVersion": "26.5.2",
        },
        {"DeviceClass": "iPad", "UniqueDeviceID": "ipad-1"},
    ])

    def fake_run_hidden(cmd, **kwargs):
        if "--help" in cmd:
            return FakeProc(stdout="help")
        if "usbmux" in cmd and "list" in cmd:
            return FakeProc(stdout=payload)
        raise AssertionError(cmd)

    monkeypatch.setattr(ios, "_run_hidden", fake_run_hidden)

    devices = ios.list_usb_devices()

    assert len(devices) == 1
    assert devices[0].udid == "udid-1"
    assert devices[0].model == "iPhone14,2"
    assert devices[0].connection == "USB"


@pytest.mark.unit
def test_ios_device_uses_coredevice_commands(monkeypatch):
    calls = []

    def fake_run(args, timeout=30, udid=None, pmd3=None):
        calls.append({"args": args, "udid": udid, "timeout": timeout})
        if args == ["amfi", "developer-mode-status"]:
            return "true"
        return ""

    monkeypatch.setattr(ios, "_run", fake_run)

    dev = ios.IosDevice(udid="udid-1")
    dev.ensure_developer_ready()
    dev.copy_text("hello")
    dev.launch_app("com.tencent.xin")

    assert calls[0]["args"] == ["amfi", "developer-mode-status"]
    assert calls[1]["args"] == ["mounter", "auto-mount"]
    assert calls[2]["args"] == ["developer", "core-device", "copy", "--userspace", "hello"]
    assert calls[3]["args"] == [
        "developer",
        "core-device",
        "launch-application",
        "--userspace",
        "com.tencent.xin",
        "noop",
    ]
    assert {call["udid"] for call in calls} == {"udid-1"}


@pytest.mark.unit
def test_diagnostics_reports_missing_pymobiledevice3(monkeypatch):
    monkeypatch.setattr(ios, "pmd3_available", lambda pmd3=None: False)

    results = ios.run_diagnostics()

    assert results == [
        ios.IosDiagnosticResult("pymobiledevice3", False, "Install with: pip install pymobiledevice3")
    ]


@pytest.mark.unit
def test_run_raises_ios_error_on_nonzero(monkeypatch):
    monkeypatch.setattr(
        ios,
        "_run_hidden",
        lambda cmd, **kwargs: FakeProc(stdout="", stderr="bad device", returncode=1),
    )

    with pytest.raises(ios.IosError, match="bad device"):
        ios._run(["usbmux", "list"])
