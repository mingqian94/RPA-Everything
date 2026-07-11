import pytest

from harness import doctor


@pytest.mark.unit
def test_check_python_requires_modern_version(monkeypatch):
    class Version:
        major = 3
        minor = 10
        micro = 9

        def __ge__(self, other):
            return (self.major, self.minor, self.micro) >= other

    monkeypatch.setattr(doctor.sys, "version_info", Version())

    result = doctor.check_python()

    assert result.name == "python"
    assert not result.ok
    assert result.required


@pytest.mark.unit
def test_check_config_missing_is_required_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "ROOT", tmp_path)

    result = doctor.check_config()

    assert result.name == "config_yaml"
    assert not result.ok
    assert result.required
    assert "config.yaml.example" in result.fix


@pytest.mark.unit
def test_check_config_rejects_template_key(monkeypatch, tmp_path):
    (tmp_path / "config.yaml").write_text("llm:\n  api_key: \"<your-anthropic-api-key>\"\n", encoding="utf-8")
    monkeypatch.setattr(doctor, "ROOT", tmp_path)

    result = doctor.check_config()

    assert not result.ok
    assert "template" in result.detail


@pytest.mark.unit
def test_run_checks_can_skip_optional(monkeypatch):
    calls = []

    monkeypatch.setattr(doctor, "check_python", lambda: calls.append("python") or doctor.Check("python", True, "ok"))
    monkeypatch.setattr(
        doctor,
        "check_python_packages",
        lambda: calls.append("packages") or doctor.Check("python_packages", True, "ok"),
    )
    monkeypatch.setattr(doctor, "check_config", lambda: calls.append("config") or doctor.Check("config", True, "ok"))
    monkeypatch.setattr(
        doctor,
        "check_chrome",
        lambda: calls.append("chrome") or doctor.Check("chrome", False, "off", required=False),
    )
    monkeypatch.setattr(
        doctor,
        "check_android",
        lambda: calls.append("android") or doctor.Check("android", False, "off", required=False),
    )
    monkeypatch.setattr(doctor, "check_ios", lambda: calls.append("ios") or doctor.Check("ios", False, "off", required=False))

    checks = doctor.run_checks(include_optional=False)

    assert [c.name for c in checks] == ["python", "python_packages", "config", "chrome"]
    assert calls == ["python", "packages", "config", "chrome"]
