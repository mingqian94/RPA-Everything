"""Preflight and failure-to-repair handoff for trace-derived Skills."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.redact import redact_text
from harness.doctor import check_android, check_chrome


ROOT = Path(__file__).parent.parent
_DRIFT_MARKERS = (
    "selector", "not found", "no element", "timeout", "stale", "ui changed",
    "找不到", "未找到", "超时", "元素不存在", "界面变化",
)


def load_manifest(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "skill" not in data:
        raise ValueError("Manifest JSON must contain a skill field.")
    return data


def preflight(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Check only platform prerequisites inferred from the trace evidence."""
    steps = manifest.get("evidence", {}).get("steps", [])
    tools = {str(step.get("tool", "")) for step in steps}
    checks: list[dict[str, Any]] = []
    if any(tool.startswith("browser_") for tool in tools):
        check = check_chrome()
        checks.append({"name": check.name, "ok": check.ok, "detail": check.detail, "fix": check.fix})
    if any(tool.startswith("android_") for tool in tools):
        check = check_android()
        checks.append({"name": check.name, "ok": check.ok, "detail": check.detail, "fix": check.fix})
    if not checks:
        checks.append({"name": "local_skill", "ok": True, "detail": "No browser or Android preflight is required.", "fix": ""})
    return checks


def is_probable_drift(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in _DRIFT_MARKERS)


def _process_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def repair_task(manifest: dict[str, Any], evidence: str) -> dict[str, str]:
    skill = str(manifest.get("skill", ""))
    trace = str(manifest.get("trace", ""))
    return {
        "status": "needs_repair",
        "goal": (
            f"Repair UI drift in deterministic Skill {skill}. Start from trace {trace}; inspect the redacted failure evidence, "
            "prefer MCP/CLI/API or DOM/UI-node/template evidence over coordinates, and do not submit, publish, send, approve, pay, delete, or mutate remote data."
        ),
        "evidence": redact_text(evidence[-2000:]),
    }


def _record_supervised_run(manifest_path: str, manifest: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Persist only a redacted summary of an explicitly requested supervised execution."""
    review = manifest.setdefault("review", {})
    review["last_supervised_run"] = {
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "status": result.get("status", "unknown"),
        "exit_code": result.get("exit_code"),
        "evidence_available": bool(result.get("evidence")),
    }
    Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    result["last_supervised_run"] = review["last_supervised_run"]
    return result


def supervise_manifest(manifest_path: str, execute: bool = False) -> dict[str, Any]:
    """Preflight a manifest, optionally execute it once, and stop on suspected drift."""
    manifest = load_manifest(manifest_path)
    if manifest.get("status") != "ready_for_supervised_run":
        return {
            "status": "needs_review",
            "reason": "Manifest has unresolved review reasons; supervised execution is blocked.",
            "review_reasons": manifest.get("review_reasons", []),
        }

    checks = preflight(manifest)
    failed = [check for check in checks if not check["ok"]]
    if failed:
        return {"status": "preflight_failed", "checks": checks, "next": "Fix the failed prerequisite, then rerun supervise."}
    if not execute:
        return {
            "status": "ready_for_supervised_run",
            "checks": checks,
            "next": "Review the manifest, then rerun with --run while watching the first execution.",
        }

    skill = Path(str(manifest["skill"])).resolve()
    if not skill.is_relative_to(ROOT.resolve()):
        return {"status": "error", "error": "Manifest skill must stay inside the RPA-Everything repository."}
    if not skill.exists():
        return {"status": "error", "error": f"Skill file not found: {skill}"}

    try:
        result = subprocess.run(
            [sys.executable, "run.py", str(skill.relative_to(ROOT).with_suffix(""))],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        evidence = _process_text(exc.stdout) + "\n" + _process_text(exc.stderr) + "\nSkill timed out after 300 seconds."
        return _record_supervised_run(manifest_path, manifest, {"checks": checks, **repair_task(manifest, evidence)})
    output = redact_text((result.stdout + "\n" + result.stderr).strip())
    if result.returncode != 0:
        if is_probable_drift(output):
            return _record_supervised_run(manifest_path, manifest, {"checks": checks, **repair_task(manifest, output)})
        return _record_supervised_run(manifest_path, manifest, {
            "status": "failed", "checks": checks, "exit_code": result.returncode, "evidence": output[-2000:],
        })
    return _record_supervised_run(manifest_path, manifest, {
        "status": "needs_result_review",
        "checks": checks,
        "exit_code": 0,
        "evidence": output[-2000:],
        "next": "The process exited successfully. Verify the declared business result and saved evidence before scheduling this Skill.",
    })


def _argv() -> list[str]:
    try:
        return sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        return sys.argv[1:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight and supervise a trace-derived Skill.")
    parser.add_argument("--manifest", required=True, help="Manifest from harness/solidify.")
    parser.add_argument("--run", action="store_true", help="Run once after preflight; never bypasses manifest review.")
    args = parser.parse_args(_argv())
    print(json.dumps(supervise_manifest(args.manifest, execute=args.run), ensure_ascii=False, indent=2))
