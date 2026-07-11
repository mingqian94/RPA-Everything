"""Read-only runtime context for Agents using the local Harness."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any

from core.capabilities import build_skill_registry
from core.skills import list_skills
from harness.doctor import Check, run_checks


def _check_payload(check: Check) -> dict[str, Any]:
    return {
        "name": check.name,
        "status": "ok" if check.ok else ("warn" if not check.required else "fail"),
        "detail": check.detail,
        "fix": check.fix,
        "required": check.required,
    }


def _capability_summary() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for name, spec in build_skill_registry().items():
        grouped[spec.get("type", "unknown")].append({
            "name": name,
            "side_effect_level": spec.get("side_effect_level", "unknown"),
        })
    return {kind: sorted(items, key=lambda item: item["name"]) for kind, items in sorted(grouped.items())}


def _recommended_next_command(checks: list[Check]) -> str:
    required_failed = [check for check in checks if check.required and not check.ok]
    if required_failed:
        return "python run.py harness/doctor --fix"
    return 'python run.py harness/agent -- --goal "Describe the task, plan it first, and do not submit or publish anything." --dry-run'


def build_runtime_snapshot(include_optional: bool = True) -> dict[str, Any]:
    """Return deterministic local context without changing browser, device, or account state."""
    checks = run_checks(include_optional=include_optional)
    required_ready = not any(check.required and not check.ok for check in checks)
    capabilities = _capability_summary()
    skills = list_skills()
    return {
        "version": 1,
        "ready": required_ready,
        "checks": [_check_payload(check) for check in checks],
        "capabilities": capabilities,
        "skills": skills,
        "safety": {
            "external_actions": "Require explicit --confirm-external before publish, send, approve, pay, delete, or remote mutation.",
            "secrets": "Use ${secret:name} backed by RPA_SECRET_NAME; do not store secrets in Skills, traces, or docs.",
            "handoff": "Use handoff_on_login only when an Agent should return needs_human_step instead of waiting for local login.",
        },
        "recommended_next_command": _recommended_next_command(checks),
    }


def _argv() -> list[str]:
    import sys

    try:
        return sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        return sys.argv[1:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print read-only runtime context for an RPA-Everything Agent.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--required-only", action="store_true", help="Skip optional Android and iPhone checks.")
    args = parser.parse_args(_argv())

    snapshot = build_runtime_snapshot(include_optional=not args.required_only)
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return

    print("RPA-Everything runtime snapshot\n")
    print(f"Ready: {'yes' if snapshot['ready'] else 'no'}")
    for check in snapshot["checks"]:
        print(f"[{check['status'].upper()}] {check['name']}: {check['detail']}")
    print("\nCapabilities:")
    for kind, items in snapshot["capabilities"].items():
        print(f"  {kind}: {len(items)}")
    print(f"Skills: {len(snapshot['skills'])}")
    print(f"\nNext: {snapshot['recommended_next_command']}")
