"""Turn a reviewed Harness trace into a deterministic, supervised-run Skill."""

from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

from harness.agent import export_trace
from harness.trace import iter_tool_calls, load_trace, replay_trace_sync

_REVIEW_TOOLS = {"desktop_click", "desktop_type", "desktop_hotkey", "browser_evaluate"}
_SIDE_EFFECT_WORDS = {"publish", "send", "approve", "delete", "pay", "submit"}


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
        "version": 1,
        "trace": str(Path(trace_path)),
        "skill": str(output),
        "dry_run_steps": dry_run,
        "syntax_checked": True,
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
