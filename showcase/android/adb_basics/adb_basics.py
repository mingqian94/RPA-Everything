"""Android ADB basics showcase."""

import argparse
import json
import sys

from core.android import AndroidDevice, list_devices, run_diagnostics
from core.logger import SkillLogger


def _argv() -> list[str]:
    try:
        sep = sys.argv.index("--")
        return sys.argv[sep + 1:]
    except ValueError:
        return sys.argv[1:]


def main():
    parser = argparse.ArgumentParser(description="Android ADB basics showcase")
    parser.add_argument("--serial", default="", help="ADB serial. Defaults to the first online device.")
    parser.add_argument("--devices", action="store_true", help="List online Android devices.")
    parser.add_argument("--diagnostics", action="store_true", help="Run non-destructive diagnostics.")
    parser.add_argument("--diagnostics-input", action="store_true", help="Also send KEYCODE_HOME during diagnostics.")
    parser.add_argument("--diagnostics-file", action="store_true", help="Also push and delete a tiny probe file.")
    parser.add_argument("--screenshot", help="Save a device screenshot to this PNG path.")
    parser.add_argument("--tap", nargs=2, type=int, metavar=("X", "Y"), help="Tap absolute pixels.")
    parser.add_argument("--tap-ratio", nargs=2, type=float, metavar=("RX", "RY"), help="Tap by screen ratio.")
    parser.add_argument("--swipe", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"), help="Swipe absolute pixels.")
    parser.add_argument("--swipe-ratio", nargs=4, type=float, metavar=("RX1", "RY1", "RX2", "RY2"), help="Swipe by screen ratio.")
    parser.add_argument("--duration-ms", type=int, default=300, help="Swipe duration in milliseconds.")
    parser.add_argument("--key", help="Android keyevent, for example KEYCODE_HOME or KEYCODE_BACK.")
    parser.add_argument("--push", nargs=2, metavar=("LOCAL", "REMOTE"), help="Push a local file to the device.")
    parser.add_argument("--media-scan", action="store_true", help="Run Android media scan after --push.")
    args = parser.parse_args(_argv())

    log = SkillLogger("android/adb_basics")

    if args.devices:
        devices = [d.__dict__ for d in list_devices()]
        print(json.dumps(devices, ensure_ascii=False, indent=2))
        log.finish({"devices": devices})
        return

    if args.diagnostics:
        results = [r.__dict__ for r in run_diagnostics(
            serial=args.serial or None,
            include_input_check=args.diagnostics_input,
            include_file_check=args.diagnostics_file,
        )]
        print(json.dumps(results, ensure_ascii=False, indent=2))
        log.finish({"diagnostics": results})
        return

    dev = AndroidDevice(serial=args.serial or None)

    if args.screenshot:
        path = dev.screencap_to(args.screenshot)
        log.step(f"Saved Android screenshot: {path}")
        log.finish({"screenshot": str(path)})
        return

    if args.tap:
        dev.tap(args.tap[0], args.tap[1])
        log.finish({"tap": args.tap})
        return

    if args.tap_ratio:
        dev.tap_ratio(args.tap_ratio[0], args.tap_ratio[1])
        log.finish({"tap_ratio": args.tap_ratio})
        return

    if args.swipe:
        dev.swipe(args.swipe[0], args.swipe[1], args.swipe[2], args.swipe[3], args.duration_ms)
        log.finish({"swipe": args.swipe, "duration_ms": args.duration_ms})
        return

    if args.swipe_ratio:
        dev.swipe_ratio(args.swipe_ratio[0], args.swipe_ratio[1], args.swipe_ratio[2], args.swipe_ratio[3], args.duration_ms)
        log.finish({"swipe_ratio": args.swipe_ratio, "duration_ms": args.duration_ms})
        return

    if args.key:
        dev.key(args.key)
        log.finish({"key": args.key})
        return

    if args.push:
        local, remote = args.push
        dev.push(local, remote)
        if args.media_scan:
            dev.media_scan(remote)
        log.finish({"pushed": {"local": local, "remote": remote, "media_scan": args.media_scan}})
        return

    parser.print_help()


if __name__ == "__main__":
    main()
