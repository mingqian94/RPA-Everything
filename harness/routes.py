"""Deterministic control-route metadata for Harness plans and traces."""

from __future__ import annotations

from typing import Any


def route_for_skill(skill_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Describe the selected automation route and safe fallbacks.

    This is explanation metadata, not a permission bypass. In particular, an
    unavailable direct integration must be surfaced instead of silently opening
    a browser or clicking a desktop UI.
    """
    path = str(spec.get("path", ""))
    kind = str(spec.get("type", ""))

    if path.startswith("showcase/app/integration/"):
        return {
            "selected": "direct_integration",
            "reason": "A registered MCP/CLI/API Skill is available for this application.",
            "fallbacks": ["stop_and_report_unavailable"],
            "vision": "forbidden unless the user explicitly chooses a separate UI workflow",
        }
    if "click_by_vision" in path:
        return {
            "selected": "browser_vision",
            "reason": "This Skill explicitly demonstrates the last-resort browser vision route.",
            "fallbacks": ["human_confirmation"],
            "vision": "selected only after DOM/structured routes are unavailable",
        }
    if kind == "browser" or path.startswith("showcase/web/"):
        return {
            "selected": "browser_dom",
            "reason": "Browser tasks prefer selectors, page text, and DOM extraction.",
            "fallbacks": ["browser_vision_with_review", "human_confirmation"],
            "vision": "last resort after DOM evidence is unavailable",
        }
    if kind == "android":
        return {
            "selected": "android_ui_node",
            "reason": "Android tasks prefer UIAutomator text/resource-id/content-desc nodes.",
            "fallbacks": ["android_ratio_coordinate", "human_confirmation"],
            "vision": "not a default Android fallback",
        }
    if kind == "desktop" or path.startswith("showcase/app/desktop/"):
        return {
            "selected": "desktop_ui_or_template",
            "reason": "Desktop tasks prefer UI Automation or local image templates.",
            "fallbacks": ["desktop_vision_with_review", "human_confirmation"],
            "vision": "last resort after UI nodes and templates are unavailable",
        }
    if path.startswith("showcase/mobile/android/"):
        return {
            "selected": "android_ui_node",
            "reason": "The saved Skill operates Android through structured ADB/UI-node actions.",
            "fallbacks": ["android_ratio_coordinate", "human_confirmation"],
            "vision": "not a default Android fallback",
        }
    if path.startswith("showcase/mobile/ios/"):
        return {
            "selected": "ios_assist",
            "reason": "iPhone support is assistive: prepare, copy, launch, and capture evidence.",
            "fallbacks": ["human_confirmation"],
            "vision": "not supported for remote iPhone control",
        }
    if path.startswith("showcase/office/"):
        return {
            "selected": "local_file_api",
            "reason": "Office Skills operate local file formats without opening an application.",
            "fallbacks": ["stop_and_report_unavailable"],
            "vision": "not applicable",
        }
    return {
        "selected": "saved_skill",
        "reason": "Run the reviewed Skill through its declared CLI interface.",
        "fallbacks": ["human_confirmation"],
        "vision": "not assumed",
    }


def annotate_tasks(tasks: list[dict[str, Any]], registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return copied plan tasks with deterministic route metadata."""
    annotated = []
    for task in tasks:
        item = dict(task)
        skill_name = str(item.get("skill", ""))
        item["route"] = route_for_skill(skill_name, registry.get(skill_name, {}))
        annotated.append(item)
    return annotated


def route_for_trace_result(result: dict[str, Any]) -> dict[str, Any]:
    """Recover a conservative route for legacy traces without route metadata."""
    route = result.get("route")
    if isinstance(route, dict) and route.get("selected"):
        return route

    tools = [str(item.get("tool", "")) for item in result.get("trace", [])]
    if any(tool.startswith("android_") for tool in tools):
        return route_for_skill("android_explore", {"type": "android"})
    if any(tool.startswith("desktop_") for tool in tools):
        return route_for_skill("desktop_explore", {"type": "desktop"})
    if any(tool.startswith("browser_") for tool in tools):
        return route_for_skill("browser_explore", {"type": "browser"})
    return route_for_skill("saved_skill", {"type": "skill"})
