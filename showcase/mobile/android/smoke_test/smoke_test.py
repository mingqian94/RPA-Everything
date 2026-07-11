"""Android real-device smoke test."""

from __future__ import annotations

import argparse
import json
import sys

from core.artifacts import write_json_artifact
from core.android import run_diagnostics
from core.logger import SkillLogger


def _argv() -> list[str]:
    try:
        sep = sys.argv.index("--")
        return sys.argv[sep + 1:]
    except ValueError:
        return sys.argv[1:]


def main():
    parser = argparse.ArgumentParser(description="Android real-device smoke test")
    parser.add_argument("--serial", default="", help="ADB serial. Defaults to first online device.")
    parser.add_argument("--include-input-check", action="store_true", help="Also send KEYCODE_HOME.")
    parser.add_argument("--include-file-check", action="store_true", help="Also push and delete a tiny probe file.")
    parser.add_argument("--output", default="", help="Output JSON path.")
    args = parser.parse_args(_argv())

    log = SkillLogger("android/smoke_test")
    results = [r.__dict__ for r in run_diagnostics(
        serial=args.serial or None,
        include_input_check=args.include_input_check,
        include_file_check=args.include_file_check,
    )]
    ok = all(item["ok"] for item in results if item["name"] != "adbkeyboard")
    payload = {"ok": ok, "results": results}
    path = write_json_artifact(payload, "android/smoke_test", args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    log.finish({"ok": ok, "output": str(path)})
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
