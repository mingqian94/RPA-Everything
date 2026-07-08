"""Lightweight Harness evaluation runner.

Static mode validates the capability catalog and safety metadata without calling
an LLM. Live mode asks the Harness planner and checks selected Skills/args.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from harness import agent as harness


CASES = Path(__file__).with_name("cases.json")


def load_cases(path: str | Path = CASES) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _contains_all(text: str, terms: list[str]) -> bool:
    return all(term in text for term in terms)


def run_static(cases: list[dict]) -> list[dict]:
    registry_text = json.dumps(harness._registry_for_planner(), ensure_ascii=False)
    results = []
    for case in cases:
        ok = True
        reasons = []
        expected = case.get("expected_skill")
        if expected and expected not in harness.SKILL_REGISTRY:
            ok = False
            reasons.append(f"missing expected skill: {expected}")
        if expected and expected in harness.SKILL_REGISTRY:
            spec = harness.SKILL_REGISTRY[expected]
            args_schema = spec.get("args_schema") or []
            names = {name for item in args_schema for name in item.get("names", [])}
            for arg in case.get("required_args", []):
                if arg not in names:
                    ok = False
                    reasons.append(f"required arg not in schema: {arg}")
            if case.get("external_should_require_confirmation") and spec.get("side_effect_level") not in {"external_draft", "external_commit"}:
                ok = False
                reasons.append("external case is not marked as draft/commit")
        if not _contains_all(registry_text, case.get("required_prompt_terms", [])):
            ok = False
            reasons.append("required planner hint terms missing")
        results.append({"id": case["id"], "ok": ok, "reasons": reasons})
    return results


def run_live(cases: list[dict]) -> list[dict]:
    results = []
    for case in cases:
        try:
            tasks = harness.plan(case["goal"])
        except Exception as exc:
            results.append({"id": case["id"], "ok": False, "reasons": [str(exc)]})
            continue
        first = tasks[0] if tasks else {}
        ok = True
        reasons = []
        if case.get("expected_skill") and first.get("skill") != case["expected_skill"]:
            ok = False
            reasons.append(f"expected {case['expected_skill']}, got {first.get('skill')}")
        args = first.get("args") or []
        for arg in case.get("required_args", []):
            if arg not in args:
                ok = False
                reasons.append(f"missing planned arg: {arg}")
        for arg in case.get("forbidden_args", []):
            if arg in args:
                ok = False
                reasons.append(f"forbidden planned arg: {arg}")
        results.append({"id": case["id"], "ok": ok, "reasons": reasons, "tasks": tasks})
    return results


def main():
    parser = argparse.ArgumentParser(description="Run Harness eval cases")
    parser.add_argument("--cases", default=str(CASES), help="Path to eval case JSON.")
    parser.add_argument("--live", action="store_true", help="Call the live Harness planner.")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results = run_live(cases) if args.live else run_static(cases)
    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"mode": "live" if args.live else "static", "ok": not failed, "results": results}, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
