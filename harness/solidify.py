"""Turn a reviewed Harness trace into a deterministic, supervised-run Skill."""

from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

from harness.agent import export_trace
from harness.routes import route_for_trace_result
from harness.trace import iter_tool_calls, load_trace, replay_trace_sync

_REVIEW_TOOLS = {"desktop_click", "desktop_type", "desktop_hotkey", "browser_evaluate"}
_SIDE_EFFECT_WORDS = {"publish", "send", "approve", "delete", "pay", "submit"}


def _evidence_level(tool: str, args: dict[str, Any]) -> str:
    """Describe the concrete evidence used by a trace step without overstating reliability."""
    if tool == "android_tap_element":
        return "ui_node"
    if tool in {"browser_click", "browser_type"} and args.get("selector"):
        return "dom_selector"
    if tool in {"desktop_click", "android_tap", "android_swipe"}:
        return "coordinate"
    if tool.startswith("desktop_"):
        return "desktop_command"
    if tool == "browser_evaluate":
        return "browser_script_review"
    if tool.startswith("browser_"):
        return "browser_command"
    if tool.startswith("android_"):
        return "android_command"
    return "command"


def summarize_evidence(record: dict[str, Any]) -> dict[str, Any]:
    steps = []
    counts: dict[str, int] = {}
    for _, item in iter_tool_calls(record):
        tool = item["tool"]
        level = _evidence_level(tool, item.get("args", {}))
        counts[level] = counts.get(level, 0) + 1
        steps.append({"tool": tool, "level": level})
    return {"counts": counts, "steps": steps}


def assess_trace(record: dict[str, Any]) -> dict[str, Any]:
    review_reasons: list[str] = []
    tool_count = 0
    for _, item in iter_tool_calls(record):
        tool_count += 1
        tool = item["tool"]
        if tool in _REVIEW_TOOLS:
            review_reasons.append(f"{tool} needs a stable selector or template review")
        text = json.dumps(item.get("args", {}), ensure_ascii=False).lower()
        if "<redacted" in text:
            review_reasons.append(f"{tool} contains redacted runtime data; replace it with an argument or secret reference")
        if any(word in text for word in _SIDE_EFFECT_WORDS):
            review_reasons.append(f"{tool} may cause an external side effect")
    if tool_count == 0:
        review_reasons.append("trace contains no replayable tool calls")
    return {
        "tool_count": tool_count,
        "review_reasons": sorted(set(review_reasons)),
        "status": "needs_review" if review_reasons else "ready_for_supervised_run",
    }


def supervision_contract(record: dict[str, Any]) -> dict[str, Any]:
    """Declare preflight, result review, and repair behavior without running a Skill."""
    tools = [item["tool"] for _, item in iter_tool_calls(record)]
    preflight = []
    if any(tool.startswith("browser_") for tool in tools):
        preflight.append("Chrome DevTools must be reachable at the configured CDP endpoint.")
    if any(tool.startswith("android_") for tool in tools):
        preflight.append("The recorded Android device must be online and authorized through ADB.")
    if not preflight:
        preflight.append("Review local input files and declared command prerequisites.")
    return {
        "preflight": preflight,
        "result_review": "A zero process exit is not proof of a business result; inspect declared output or visible evidence before scheduling.",
        "drift_recovery": (
            "On selector/template/UI-node failure, stop without retrying external actions, preserve redacted output, "
            "and return a repair task based on the original trace."
        ),
    }


def build_skill_review(record: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    """Create a concise human review surface from trace facts, not claims of safety."""
    tools = [item["tool"] for _, item in iter_tool_calls(record)]
    platforms: list[str] = []
    permissions: list[str] = []
    if any(tool.startswith("browser_") for tool in tools):
        platforms.append("browser")
        permissions.append("Chrome DevTools access to the dedicated RPA browser profile")
    if any(tool.startswith("android_") for tool in tools):
        platforms.append("android")
        permissions.append("Authorized Android Debug Bridge (ADB) device")
    if any(tool.startswith("desktop_") for tool in tools):
        platforms.append("desktop")
        permissions.append("Local desktop accessibility and screen-control permission")
    if any(tool.startswith("ios_") for tool in tools):
        platforms.append("ios_assist")
        permissions.append("Connected iPhone with the documented assist prerequisites")
    if not platforms:
        platforms.append("local")
        permissions.append("Local files and declared command prerequisites")

    serialized_calls = "\n".join(json.dumps(item.get("args", {}), ensure_ascii=False).lower()
                                  for _, item in iter_tool_calls(record))
    external_risk = "external_action_review_required" if any(word in serialized_calls for word in _SIDE_EFFECT_WORDS) else "none_detected"
    checklist = [
        "Confirm the target system, account scope, and expected business result.",
        "Check each preflight requirement on the target machine.",
        "Review generated code and every non-selector/coordinate action before the first run.",
        "Run once under supervision and inspect the business result before scheduling.",
    ]
    if external_risk != "none_detected":
        checklist.insert(3, "Keep the final external action behind an explicit human confirmation.")
    if assessment["review_reasons"]:
        checklist.insert(3, "Resolve every manifest review reason before running the Skill.")
    return {
        "target_platforms": platforms,
        "required_permissions": permissions,
        "input_assumptions": [
            "The trace represents one reviewed workflow and does not contain real secrets.",
            "Runtime values must be supplied as arguments or ${secret:name} references, not copied from the trace.",
        ],
        "external_action_risk": external_risk,
        "checklist": checklist,
        "last_supervised_run": None,
    }


def solidify_trace(trace_path: str, output_path: str) -> dict[str, Any]:
    """Export, syntax-check, and assess a trace-derived Skill without executing it."""
    record = load_trace(trace_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_trace(str(record.get("goal", "")), list(record.get("results", [])), str(output))
    py_compile.compile(str(output), doraise=True)
    assessment = assess_trace(record)
    dry_run = replay_trace_sync(record, dry_run=True)
    manifest = {
        "version": 2,
        "trace": str(Path(trace_path)),
        "skill": str(output),
        "dry_run_steps": dry_run,
        "syntax_checked": True,
        "evidence": summarize_evidence(record),
        "routes": [route_for_trace_result(result) for result in record.get("results", [])],
        "supervision": supervision_contract(record),
        "review": build_skill_review(record, assessment),
        **assessment,
        "next_step": "Run once under supervision and review evidence before scheduling.",
    }
    manifest_path = output.with_name(f"{output.stem}.manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest"] = str(manifest_path)
    return manifest


def _argv() -> list[str]:
    try:
        return sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        return sys.argv[1:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Solidify a Harness trace into a supervised-run Skill.")
    parser.add_argument("--trace", required=True, help="Trace JSON exported by harness/agent --trace-json.")
    parser.add_argument("--output", required=True, help="Skill Python path, such as skills/my_workflow.py.")
    args = parser.parse_args(_argv())
    print(json.dumps(solidify_trace(args.trace, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
