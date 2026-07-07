import pytest

from core import android


@pytest.mark.unit
def test_list_devices_filters_mdns(monkeypatch):
    output = """List of devices attached
127.0.0.1:5555 device product:x model:Pixel_8 device:oriole
adb-xyz._adb-tls-connect._tcp device product:x model:Duplicate device:x
offline123 offline
"""

    monkeypatch.setattr(android, "_run_global", lambda args, adb=None, timeout=20: (output, "", 0))

    devices = android.list_devices()

    assert len(devices) == 1
    assert devices[0].serial == "127.0.0.1:5555"
    assert devices[0].model == "Pixel_8"


@pytest.mark.unit
def test_list_devices_can_include_offline(monkeypatch):
    output = """List of devices attached
abc123 offline
"""

    monkeypatch.setattr(android, "_run_global", lambda args, adb=None, timeout=20: (output, "", 0))

    devices = android.list_devices(include_offline=True)

    assert len(devices) == 1
    assert devices[0].state == "offline"


@pytest.mark.unit
def test_tap_ratio_converts_to_pixels(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    dev._resolution = (1080, 2400)
    calls = []

    monkeypatch.setattr(dev, "resolution", lambda: (1080, 2400))
    monkeypatch.setattr(dev, "tap", lambda x, y: calls.append((x, y)))

    dev.tap_ratio(0.5, 0.25)

    assert calls == [(540, 600)]


@pytest.mark.unit
def test_tap_ratio_rejects_out_of_range(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    monkeypatch.setattr(dev, "resolution", lambda: (100, 100))

    with pytest.raises(ValueError):
        dev.tap_ratio(1.2, 0.5)


@pytest.mark.unit
def test_diagnostics_returns_connection_error(monkeypatch):
    def fail_init(self, serial=None, adb=None):
        raise android.AdbError("no adb")

    monkeypatch.setattr(android.AndroidDevice, "__init__", fail_init)

    results = android.run_diagnostics()

    assert len(results) == 1
    assert results[0].name == "adb_connection"
    assert not results[0].ok
