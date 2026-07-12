import pytest
import runpy
import sys

from harness import runtime
from harness.doctor import Check


@pytest.mark.unit
def test_runtime_snapshot_reports_capabilities_and_safe_next_step(monkeypatch):
    monkeypatch.setattr(runtime, "run_checks", lambda include_optional: [
        Check("python", True, "3.11"),
        Check("chrome_cdp", False, "off", required=False),
    ])
    monkeypatch.setattr(runtime, "build_skill_registry", lambda: {
        "browser_explore": {"type": "browser", "side_effect_level": "unknown"},
        "local_report": {"type": "skill", "side_effect_level": "none"},
    })
    monkeypatch.setattr(runtime, "list_skills", lambda: ["skills/local_report"])

    snapshot = runtime.build_runtime_snapshot(include_optional=False)

    assert snapshot["ready"]
    assert snapshot["capabilities"]["browser"][0]["name"] == "browser_explore"
    assert snapshot["skills"] == ["skills/local_report"]
    assert "--dry-run" in snapshot["recommended_next_command"]


@pytest.mark.unit
def test_runtime_snapshot_recommends_doctor_fix_for_required_failure(monkeypatch):
    monkeypatch.setattr(runtime, "run_checks", lambda include_optional: [
        Check("config_yaml", False, "missing", required=True),
    ])
    monkeypatch.setattr(runtime, "build_skill_registry", lambda: {})
    monkeypatch.setattr(runtime, "list_skills", lambda: [])

    snapshot = runtime.build_runtime_snapshot()

    assert not snapshot["ready"]
    assert snapshot["recommended_next_command"] == "python run.py harness/doctor --fix"


@pytest.mark.unit
def test_run_entrypoint_dispatches_runtime(monkeypatch):
    called = []
    monkeypatch.setattr(sys, "argv", ["run.py", "harness/runtime", "--required-only"])
    monkeypatch.setattr(runtime, "main", lambda: called.append(list(sys.argv)))

    runpy.run_path(str(runtime.__file__).replace("harness\\runtime.py", "run.py"), run_name="__main__")

    assert called[0][1:] == ["--required-only"]


@pytest.mark.unit
def test_run_entrypoint_dispatches_demo(monkeypatch):
    from harness import demo

    called = []
    monkeypatch.setattr(sys, "argv", ["run.py", "harness/demo", "--json"])
    monkeypatch.setattr(demo, "main", lambda: called.append(list(sys.argv)))

    runpy.run_path(str(demo.__file__).replace("harness\\demo.py", "run.py"), run_name="__main__")

    assert called[0][1:] == ["--json"]
