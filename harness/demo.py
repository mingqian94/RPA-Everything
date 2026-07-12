"""A no-key, no-network first-run walkthrough for the Harness lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harness.solidify import assess_trace, summarize_evidence
from harness.trace import load_trace, replay_trace_sync


ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "harness" / "fixtures" / "first_run_trace.json"


def build_first_run_demo() -> dict[str, Any]:
    """Return an inspectable lifecycle preview without changing local state."""
    record = load_trace(FIXTURE)
    steps = replay_trace_sync(record, dry_run=True)
    assessment = assess_trace(record)
    return {
        "version": 1,
        "status": "ready_to_inspect",
        "guarantees": {
            "llm_key_required": False,
            "network_used": False,
            "external_action": False,
            "files_written": False,
        },
        "lifecycle": [
            {"step": "doctor", "command": "python run.py harness/doctor --fix --required-only", "note": "Creates only a missing config template."},
            {"step": "runtime", "command": "python run.py harness/runtime --json", "note": "Reports readiness and safety boundaries."},
            {"step": "replay", "command": "python run.py harness/replay -- --trace harness/fixtures/first_run_trace.json --dry-run", "note": "Lists replayable steps without opening a browser."},
            {"step": "inspect", "command": "python run.py harness/solidify -- --trace <your-trace.json> --output skills/my_workflow.py", "note": "Real traces become a reviewed Skill and manifest."},
        ],
        "fixture": str(FIXTURE.relative_to(ROOT).as_posix()),
        "dry_run_steps": steps,
        "evidence": summarize_evidence(record),
        "assessment": assessment,
        "next": "Configure an LLM only after this preview is understood; then ask the Harness to plan a read-only task with --dry-run.",
    }


def _argv() -> list[str]:
    try:
        return sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        return sys.argv[1:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the no-key, no-side-effect Harness first-run preview.")
    parser.add_argument("--json", action="store_true", help="Print only JSON.")
    args = parser.parse_args(_argv())
    result = build_first_run_demo()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("RPA-Everything first-run preview\n")
    print("This preview does not use an LLM key, network, browser, or external account.\n")
    for item in result["lifecycle"]:
        print(f"{item['step']}: {item['command']}")
        print(f"  {item['note']}")
    print(f"\nReplayable bundled steps: {len(result['dry_run_steps'])}")
    print(f"Evidence: {result['evidence']['counts']}")
    print(f"\nNext: {result['next']}")
