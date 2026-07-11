import json

import pytest

from harness.solidify import solidify_trace


@pytest.mark.unit
def test_solidify_trace_exports_checked_skill_and_manifest(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({
        "version": 1,
        "goal": "open a page",
        "results": [{"label": "browser", "trace": [
            {"tool": "browser_navigate", "args": {"url": "https://example.com"}, "is_error": False},
            {"tool": "browser_click", "args": {"selector": "#go"}, "is_error": False},
        ]}],
    }), encoding="utf-8")
    output = tmp_path / "example_skill.py"

    result = solidify_trace(str(trace), str(output))

    assert output.exists()
    assert (tmp_path / "example_skill.manifest.json").exists()
    assert result["syntax_checked"]
    assert result["status"] == "ready_for_supervised_run"
    assert result["tool_count"] == 2
    assert result["evidence"]["counts"] == {"browser_command": 1, "dom_selector": 1}


@pytest.mark.unit
def test_solidify_flags_desktop_coordinate_actions(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({
        "results": [{"trace": [
            {"tool": "desktop_click", "args": {"x": 1, "y": 2}, "is_error": False},
        ]}],
    }), encoding="utf-8")

    result = solidify_trace(str(trace), str(tmp_path / "desktop_skill.py"))

    assert result["status"] == "needs_review"
    assert "desktop_click" in result["review_reasons"][0]


@pytest.mark.unit
def test_solidify_flags_redacted_runtime_data(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({
        "results": [{"trace": [
            {"tool": "android_type", "args": {"text": "<redacted-phone>"}, "is_error": False},
        ]}],
    }), encoding="utf-8")

    result = solidify_trace(str(trace), str(tmp_path / "input_skill.py"))

    assert result["status"] == "needs_review"
    assert "redacted runtime data" in result["review_reasons"][0]


@pytest.mark.unit
def test_solidify_records_coordinate_evidence(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({
        "results": [{"trace": [
            {"tool": "android_tap_element", "args": {"text": "Next"}, "is_error": False},
            {"tool": "android_tap", "args": {"rx": 0.5, "ry": 0.5}, "is_error": False},
        ]}],
    }), encoding="utf-8")

    result = solidify_trace(str(trace), str(tmp_path / "mobile_skill.py"))

    assert result["evidence"]["counts"] == {"ui_node": 1, "coordinate": 1}
