"""iPhone semi-automation showcase.

This intentionally stops at copy-text / launch-app / screenshot. iOS remote
touch is not claimed here because CoreDevice HID control is not generally
available on the tested iOS 26.x devices without additional WDA/XCUITest setup.
"""

from __future__ import annotations

import argparse
import json
import sys

from core.artifacts import write_json_artifact
from core.ios import IosDevice, list_devices, run_diagnostics
from core.logger import SkillLogger


def _argv() -> list[str]:
    try:
        sep = sys.argv.index("--")
        return sys.argv[sep + 1:]
    except ValueError:
        return sys.argv[1:]


def main():
    parser = argparse.ArgumentParser(description="iPhone semi-automation assistant")
    parser.add_argument("--udid", default="", help="iPhone UDID. Defaults to the first USB iPhone.")
    parser.add_argument("--devices", action="store_true", help="List visible iPhones.")
    parser.add_argument("--include-wifi", action="store_true", help="Also try best-effort WiFi discovery.")
    parser.add_argument("--diagnostics", action="store_true", help="Run iPhone semi-automation diagnostics.")
    parser.add_argument("--include-clipboard-check", action="store_true", help="Also write diagnostic text to iPhone clipboard.")
    parser.add_argument("--copy-text", default="", help="Copy text to the iPhone clipboard.")
    parser.add_argument("--launch-app", default="", help="Launch an app by bundle id, for example com.tencent.xin.")
    parser.add_argument("--launch-wechat", action="store_true", help="Launch WeChat on the iPhone.")
    parser.add_argument("--screenshot", default="", help="Save an iPhone screenshot to this PNG path.")
    parser.add_argument("--output", default="", help="Write JSON result to this path.")
    args = parser.parse_args(_argv())

    log = SkillLogger("mobile/iphone_assist")

    if args.devices:
        devices = [d.__dict__ for d in list_devices(include_wifi=args.include_wifi)]
        payload = {"devices": devices}
        if args.output:
            write_json_artifact(payload, "mobile/iphone_assist", args.output)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        log.finish(payload)
        return

    if args.diagnostics:
        results = [r.__dict__ for r in run_diagnostics(
            udid=args.udid or None,
            include_clipboard_check=args.include_clipboard_check,
        )]
        payload = {"ok": all(r["ok"] for r in results), "results": results}
        if args.output:
            write_json_artifact(payload, "mobile/iphone_assist", args.output)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        log.finish(payload)
        if not payload["ok"]:
            raise SystemExit(1)
        return

    dev = IosDevice(udid=args.udid or None)
    dev.ensure_developer_ready()
    actions: list[dict] = []

    if args.copy_text:
        dev.copy_text(args.copy_text)
        actions.append({"action": "copy_text", "status": "ok"})
        log.step("Copied text to iPhone clipboard")

    bundle_id = args.launch_app or ("com.tencent.xin" if args.launch_wechat else "")
    if bundle_id:
        dev.launch_app(bundle_id)
        actions.append({"action": "launch_app", "bundle_id": bundle_id, "status": "ok"})
        log.step(f"Launched iPhone app: {bundle_id}")

    if args.screenshot:
        path = dev.screenshot_to(args.screenshot)
        actions.append({"action": "screenshot", "path": str(path), "status": "ok"})
        log.step(f"Saved iPhone screenshot: {path}")

    payload = {
        "ok": True,
        "udid": dev.udid,
        "actions": actions,
        "status": "pending_manual_confirmation",
        "note": "iPhone semi-automation does not perform remote touch or final publish.",
    }
    if args.output:
        write_json_artifact(payload, "mobile/iphone_assist", args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    log.finish(payload)


if __name__ == "__main__":
    main()
