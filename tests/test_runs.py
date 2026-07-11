import json

import pytest

from harness.runs import get_run, list_runs


@pytest.mark.unit
def test_list_runs_summarizes_status_and_filters_skill(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({
        "skill": "web/export", "started_at": "2026-01-01", "finished_at": "2026-01-01",
        "steps": [{"status": "ok"}], "result": {"status": "pending_confirmation"},
    }), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({
        "skill": "android/post", "started_at": "2026-01-02", "finished_at": "2026-01-02",
        "steps": [{"status": "error"}], "result": {},
    }), encoding="utf-8")

    runs = list_runs(skill="web", log_dir=tmp_path)

    assert len(runs) == 1
    assert runs[0]["status"] == "pending_confirmation"
    assert runs[0]["skill"] == "web/export"


@pytest.mark.unit
def test_get_run_rejects_path_escape_and_redacts_detail(tmp_path):
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"skill": "test", "result": {"token": "private"}}), encoding="utf-8")

    assert get_run("run.json", log_dir=tmp_path)["result"]["token"] == "<redacted>"
    with pytest.raises(ValueError):
        get_run("../run.json", log_dir=tmp_path)
