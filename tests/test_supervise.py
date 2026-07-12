"""Supervised-run preflight and drift handoff tests."""

import json

from harness import supervise


def test_supervise_blocks_unreviewed_manifest(tmp_path):
    manifest = tmp_path / "workflow.manifest.json"
    manifest.write_text(json.dumps({
        "skill": "skills/workflow.py",
        "status": "needs_review",
        "review_reasons": ["coordinate needs review"],
    }), encoding="utf-8")

    result = supervise.supervise_manifest(str(manifest))

    assert result["status"] == "needs_review"


def test_supervise_preflight_returns_ready_without_executing(tmp_path):
    manifest = tmp_path / "workflow.manifest.json"
    manifest.write_text(json.dumps({
        "skill": "skills/workflow.py",
        "status": "ready_for_supervised_run",
        "evidence": {"steps": []},
    }), encoding="utf-8")

    result = supervise.supervise_manifest(str(manifest))

    assert result["status"] == "ready_for_supervised_run"
    assert result["checks"][0]["name"] == "local_skill"


def test_drift_detection_and_repair_task_redact_evidence():
    output = "Selector not found for user@example.com"
    repair = supervise.repair_task({"skill": "skills/workflow.py", "trace": "trace.json"}, output)

    assert supervise.is_probable_drift(output)
    assert repair["status"] == "needs_repair"
    assert "<redacted-email>" in repair["evidence"]


def test_timeout_output_bytes_are_normalized():
    assert supervise._process_text(b"selector not found") == "selector not found"


def test_supervised_run_summary_is_persisted_without_evidence(tmp_path):
    manifest_path = tmp_path / "workflow.manifest.json"
    manifest = {"skill": "skills/workflow.py", "review": {"last_supervised_run": None}}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = supervise._record_supervised_run(
        str(manifest_path), manifest, {"status": "failed", "exit_code": 1, "evidence": "private output"}
    )
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["last_supervised_run"]["status"] == "failed"
    assert result["last_supervised_run"]["evidence_available"]
    assert "evidence" not in saved["review"]["last_supervised_run"]
