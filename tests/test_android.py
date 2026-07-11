import pytest

from core import android
from core import android_profile


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
def test_adb_path_prefers_project_platform_tools(monkeypatch, tmp_path):
    bundled = tmp_path / "tools" / "platform-tools" / "adb.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_text("", encoding="utf-8")

    monkeypatch.setattr(android, "ROOT", tmp_path)
    monkeypatch.setattr(android, "_cfg_get", lambda key: "")
    monkeypatch.setattr(android.platform, "system", lambda: "Windows")

    assert android.adb_path() == str(bundled)


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
def test_shell_sends_non_ascii_command_via_stdin(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    dev.adb = "adb"
    dev.serial = "serial"
    calls = []

    def fake_run(args, binary=False, timeout=30, stdin=None):
        calls.append({"args": args, "stdin": stdin})
        return ""

    monkeypatch.setattr(dev, "_run", fake_run)

    dev.shell("mkdir -p /sdcard/Pictures/朋友圈素材")

    assert calls == [{
        "args": ["shell"],
        "stdin": "mkdir -p /sdcard/Pictures/朋友圈素材\nexit\n".encode("utf-8"),
    }]


@pytest.mark.unit
def test_parse_ui_xml_extracts_nodes():
    xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy>
  <node text="发布" resource-id="com.app:id/publish" content-desc="send" class="android.widget.Button" clickable="true" bounds="[10,20][110,80]" />
</hierarchy>"""

    nodes = android._parse_ui_xml(xml)

    assert len(nodes) == 1
    assert nodes[0].text == "发布"
    assert nodes[0].resource_id == "com.app:id/publish"
    assert nodes[0].center == (60, 50)


@pytest.mark.unit
def test_tap_ui_node_uses_uiautomator_center(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    calls = []
    monkeypatch.setattr(dev, "ui_nodes", lambda: [
        android.AndroidUiNode(text="发布", bounds=(10, 20, 110, 80)),
    ])
    monkeypatch.setattr(dev, "tap", lambda x, y: calls.append((x, y)))

    node = dev.tap_ui_node(text="发布", exact=True)

    assert node.text == "发布"
    assert calls == [(60, 50)]


@pytest.mark.unit
def test_diagnostics_returns_connection_error(monkeypatch):
    def fail_init(self, serial=None, adb=None):
        raise android.AdbError("no adb")

    monkeypatch.setattr(android.AndroidDevice, "__init__", fail_init)

    results = android.run_diagnostics()

    assert len(results) == 1
    assert results[0].name == "adb_connection"
    assert not results[0].ok


@pytest.mark.unit
def test_unicode_input_switches_and_restores_ime(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    calls = []

    def fake_shell(command, timeout=30):
        calls.append(command)
        if command == "pm list packages com.android.adbkeyboard":
            return "package:com.android.adbkeyboard"
        if command == "settings get secure default_input_method":
            return "com.vendor/.Ime\n"
        if command == "ime list -s":
            return "com.android.adbkeyboard/.AdbIME\ncom.vendor/.Ime\n"
        return ""

    monkeypatch.setattr(dev, "shell", fake_shell)

    dev.input_text("你好", unicode=True)

    assert "ime set com.android.adbkeyboard/.AdbIME" in calls
    assert any("ADB_INPUT_B64" in call for call in calls)
    assert calls[-1] == "ime set com.vendor/.Ime"


@pytest.mark.unit
def test_restore_ime_uses_preferred_when_previous_missing(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    calls = []

    monkeypatch.setattr(dev, "enabled_imes", lambda: [
        "com.android.adbkeyboard/.AdbIME",
        "com.vendor/.PreferredIme",
    ])
    monkeypatch.setattr(dev, "set_ime", lambda ime: calls.append(ime))

    restored = dev.restore_ime(previous_ime="com.old/.Ime", preferred_ime="com.vendor/.PreferredIme")

    assert restored is True
    assert calls == ["com.vendor/.PreferredIme"]


@pytest.mark.unit
def test_unicode_input_requires_adbkeyboard(monkeypatch):
    dev = android.AndroidDevice.__new__(android.AndroidDevice)
    monkeypatch.setattr(dev, "shell", lambda command, timeout=30: "")

    with pytest.raises(android.AdbError, match="ADBKeyboard"):
        dev.input_text("你好", unicode=True)


@pytest.mark.unit
def test_android_profile_roundtrip(tmp_path):
    store = tmp_path / "profiles.json"
    profile = {"coords": {"compose": {"rx": 0.5, "ry": 0.8}}, "notes": "Pixel"}

    android_profile.save_profile("Pixel 8", profile, store)

    loaded = android_profile.get_profile("Pixel 8", store)
    assert loaded["coords"]["compose"] == {"rx": 0.5, "ry": 0.8}
    assert loaded["notes"] == "Pixel"


@pytest.mark.unit
def test_android_profile_rejects_bad_ratio():
    with pytest.raises(ValueError, match="between 0 and 1"):
        android_profile.validate_profile({"coords": {"bad": {"rx": 1.2, "ry": 0.1}}})
