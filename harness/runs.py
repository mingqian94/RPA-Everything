"""Query structured Skill run logs for a terminal or MCP task center."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.logger import _LOG_DIR
from core.redact import redact


def _status(record: dict[str, Any]) -> str:
    if any(step.get("status") == "error" for step in record.get("steps", [])):
        return "error"
    result = record.get("result")
    if isinstance(result, dict):
        state = str(result.get("status", ""))
        if "error" in result or state in {"error", "failed"}:
            return "error"
        if state.startswith("pending_"):
            return state
    return "ok"


def _summary(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": path.name,
        "skill": record.get("skill", "unknown"),
        "status": _status(record),
        "started_at": record.get("started_at", ""),
        "finished_at": record.get("finished_at", ""),
        "step_count": len(record.get("steps", [])),
    }


def list_runs(skill: str = "", limit: int = 20, log_dir: Path | None = None) -> list[dict[str, Any]]:
    """List newest structured runs. Invalid or partial files are ignored."""
    directory = log_dir or _LOG_DIR
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        summary = _summary(path, record)
        if skill and skill not in summary["skill"]:
            continue
        items.append(summary)
        if len(items) >= limit:
            break
    return items


def get_run(run_id: str, log_dir: Path | None = None) -> dict[str, Any]:
    """Read one run by its filename without allowing a path escape."""
    directory = (log_dir or _LOG_DIR).resolve()
    path = (directory / run_id).resolve()
    if path.parent != directory or path.suffix != ".json":
        raise ValueError("run_id must be a JSON filename from run_list")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("run log is not a JSON object")
    return redact(record)


def _argv() -> list[str]:
    try:
        return sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        return sys.argv[1:]


def main() -> None:
    parser = argparse.ArgumentParser(description="List or inspect RPA-Everything Skill runs.")
    parser.add_argument("--skill", default="", help="Only include skill names containing this text.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum run summaries to return.")
    parser.add_argument("--show", default="", metavar="RUN_ID", help="Show one run id returned by the list.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a compact table.")
    args = parser.parse_args(_argv())

    if args.show:
        output: Any = get_run(args.show)
    else:
        output = list_runs(skill=args.skill, limit=max(1, args.limit))

    if args.json or args.show:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return
    if not output:
        print("No Skill runs recorded yet.")
        return
    for item in output:
        print(f"[{item['status']}] {item['started_at']}  {item['skill']}  id={item['id']}")


if __name__ == "__main__":
    main()
