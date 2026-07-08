"""Replay a Harness trace JSON file."""

from __future__ import annotations

import argparse
import json
import sys

from core.logger import SkillLogger
from harness.trace import load_trace, replay_trace_sync


def _argv() -> list[str]:
    try:
        sep = sys.argv.index("--")
        return sys.argv[sep + 1:]
    except ValueError:
        return sys.argv[1:]


def main():
    parser = argparse.ArgumentParser(description="Replay a Harness trace JSON file")
    parser.add_argument("--trace", required=True, help="Path to trace JSON exported by harness/agent --trace-json.")
    parser.add_argument("--dry-run", action="store_true", help="Print replay sequence without executing tools.")
    args = parser.parse_args(_argv())

    log = SkillLogger("harness/replay")
    record = load_trace(args.trace)
    replayed = replay_trace_sync(record, dry_run=args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, "count": len(replayed), "steps": replayed}, ensure_ascii=False, indent=2))
    log.finish({"dry_run": args.dry_run, "count": len(replayed)})


if __name__ == "__main__":
    main()
