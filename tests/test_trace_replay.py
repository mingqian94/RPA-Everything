import json

import pytest

from harness.trace import export_trace_json, iter_tool_calls, load_trace, replay_trace_sync


@pytest.mark.unit
def test_export_and_load_trace_json(tmp_path):
    out = tmp_path / "trace.json"
    results = [{
        "label": "android",
        "trace": [
            {"tool": "android_screenshot", "args": {}, "is_error": False},
            {"tool": "android_tap", "args": {"rx": 0.5, "ry": 0.5}, "is_error": False},
        ],
    }]

    export_trace_json("tap center", results, str(out))
    loaded = load_trace(out)

    assert loaded["version"] == 1
    assert loaded["goal"] == "tap center"
    assert loaded["results"] == results


@pytest.mark.unit
def test_replay_trace_dry_run_filters_readonly_steps():
    record = {
        "results": [{
            "trace": [
                {"tool": "browser_screenshot", "args": {}, "is_error": False},
                {"tool": "android_dump_ui", "args": {}, "is_error": False},
                {"tool": "android_tap_element", "args": {"text": "发布"}, "is_error": False},
                {"tool": "desktop_type", "args": {"text": "hello"}, "is_error": False},
            ],
        }],
    }

    replayed = replay_trace_sync(record, dry_run=True)

    assert replayed == [
        {"tool": "android_tap_element", "args": {"text": "发布"}},
        {"tool": "desktop_type", "args": {"text": "hello"}},
    ]
    assert [item["tool"] for _, item in iter_tool_calls(record)] == ["android_tap_element", "desktop_type"]


@pytest.mark.unit
def test_load_trace_rejects_bad_json_shape(tmp_path):
    out = tmp_path / "trace.json"
    out.write_text(json.dumps({"nope": []}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_trace(out)
