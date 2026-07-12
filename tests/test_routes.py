"""Control-route metadata tests."""

from harness.routes import annotate_tasks, route_for_skill, route_for_trace_result


def test_direct_integration_does_not_silently_fallback_to_ui():
    route = route_for_skill(
        "skill:showcase/app/integration/demo/read",
        {"type": "skill", "path": "showcase/app/integration/demo/read"},
    )

    assert route["selected"] == "direct_integration"
    assert route["fallbacks"] == ["stop_and_report_unavailable"]


def test_browser_and_android_routes_prefer_structured_evidence():
    tasks = annotate_tasks([
        {"skill": "browser_explore", "goal": "read", "label": "web"},
        {"skill": "android_explore", "goal": "tap", "label": "phone"},
    ], {
        "browser_explore": {"type": "browser"},
        "android_explore": {"type": "android"},
    })

    assert tasks[0]["route"]["selected"] == "browser_dom"
    assert tasks[1]["route"]["selected"] == "android_ui_node"


def test_legacy_trace_route_is_inferred_from_tools():
    route = route_for_trace_result({"trace": [{"tool": "desktop_click", "args": {}}]})

    assert route["selected"] == "desktop_ui_or_template"
