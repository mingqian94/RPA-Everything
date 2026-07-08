"""Draft a Xiaohongshu note through Android ADB.

This showcase intentionally moves slowly and stops before the final publish
button unless --confirm-post is provided.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from core.android import AndroidDevice
from core.logger import SkillLogger

REMOTE_DIR = "/sdcard/Pictures/RPA_XHS"
DEFAULT_PACKAGE = "com.xingin.xhs"

EXAMPLE_PROFILE = {
    "coords": {
        "create_button": [0.50, 0.94],
        "album_entry": [0.18, 0.83],
        "first_media": [0.14, 0.23],
        "next_button": [0.88, 0.94],
        "caption_input": [0.18, 0.42],
        "publish_button": [0.86, 0.93],
    }
}


def _argv() -> list[str]:
    try:
        sep = sys.argv.index("--")
        return sys.argv[sep + 1:]
    except ValueError:
        return sys.argv[1:]


def _sleep(min_wait: float, max_wait: float) -> None:
    time.sleep(random.uniform(min_wait, max_wait))


def _load_profile(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    coords = data.get("coords")
    if not isinstance(coords, dict):
        raise ValueError("profile must contain a coords object")
    required = ["create_button", "first_media", "next_button", "caption_input", "publish_button"]
    missing = [name for name in required if name not in coords]
    if missing:
        raise ValueError(f"profile missing coords: {', '.join(missing)}")
    return data


def _push_media(dev: AndroidDevice, paths: list[str], log: SkillLogger) -> None:
    if not paths:
        return
    dev.shell(f"mkdir -p {REMOTE_DIR}")
    batch = time.strftime("%Y%m%d_%H%M%S")
    for idx, local in enumerate(paths, 1):
        local_path = Path(local)
        if not local_path.exists():
            raise FileNotFoundError(f"media not found: {local}")
        remote = f"{REMOTE_DIR}/xhs_{batch}_{idx:02d}{local_path.suffix.lower()}"
        dev.push(local_path, remote)
        dev.media_scan(remote)
        log.step(f"Pushed media: {local_path.name} -> {remote}")
        _sleep(0.4, 0.9)


def main() -> None:
    parser = argparse.ArgumentParser(description="Xiaohongshu Android note showcase")
    parser.add_argument("--serial", default="", help="ADB serial. Defaults to the first online device.")
    parser.add_argument("--profile", default="", help="JSON file with Xiaohongshu ratio coordinates.")
    parser.add_argument("--print-example-profile", action="store_true", help="Print an example coordinate profile.")
    parser.add_argument("--caption", default="", help="Caption text. Unicode requires ADBKeyboard.")
    parser.add_argument("--media", nargs="*", default=[], help="Media files to push before selecting from album.")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="Android package to launch.")
    parser.add_argument("--no-launch", action="store_true", help="Do not launch the app first.")
    parser.add_argument("--confirm-post", action="store_true", help="Actually tap the final publish button.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned steps without touching the device.")
    parser.add_argument("--min-wait", type=float, default=1.8, help="Minimum random wait between steps.")
    parser.add_argument("--max-wait", type=float, default=4.2, help="Maximum random wait between steps.")
    parser.add_argument("--review-min", type=float, default=8.0, help="Minimum review pause before final publish.")
    parser.add_argument("--review-max", type=float, default=15.0, help="Maximum review pause before final publish.")
    args = parser.parse_args(_argv())

    if args.print_example_profile:
        print(json.dumps(EXAMPLE_PROFILE, ensure_ascii=False, indent=2))
        return

    if not args.profile:
        parser.error("--profile is required unless --print-example-profile is used")

    profile = _load_profile(args.profile)
    coords = profile["coords"]

    log = SkillLogger("android/xiaohongshu_note")
    planned = [
        "ensure device online",
        "optionally launch Xiaohongshu",
        "push media to phone album",
        "tap create button",
        "tap album entry if configured",
        "select first media",
        "tap next",
        "input caption",
        "pause for human-like review",
        "stop before publish unless --confirm-post",
    ]

    if args.dry_run:
        print(json.dumps({"planned_steps": planned, "profile": profile}, ensure_ascii=False, indent=2))
        log.finish({"dry_run": True, "planned_steps": planned})
        return

    dev = AndroidDevice(serial=args.serial or None)
    dev.ensure_online()
    log.step(f"Device online: {dev.serial}")

    if not args.no_launch:
        dev.shell(f"monkey -p {args.package} -c android.intent.category.LAUNCHER 1")
        log.step(f"Launched package: {args.package}")
        _sleep(args.min_wait, args.max_wait)

    _push_media(dev, args.media, log)

    def tap(name: str, label: str) -> None:
        rx, ry = coords[name]
        dev.tap_ratio(float(rx), float(ry))
        log.step(label)
        _sleep(args.min_wait, args.max_wait)

    tap("create_button", "Tapped create button")
    if "album_entry" in coords:
        tap("album_entry", "Tapped album entry")
    tap("first_media", "Selected first media")
    tap("next_button", "Tapped next")

    if args.caption:
        tap("caption_input", "Focused caption input")
        dev.input_text(args.caption, unicode=True)
        log.step("Typed caption through ADBKeyboard")
        _sleep(args.min_wait, args.max_wait)

    review_wait = random.uniform(args.review_min, args.review_max)
    log.step(f"Review pause before final action: {review_wait:.1f}s")
    time.sleep(review_wait)
    before = dev.screencap_to("logs/xhs_before_publish.png")
    log.step(f"Saved pre-publish screenshot: {before}")

    if not args.confirm_post:
        result = {
            "status": "pending_confirmation",
            "final_publish_clicked": False,
            "screenshot": str(before),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        log.finish(result)
        return

    tap("publish_button", "Tapped final publish button")
    after = dev.screencap_to("logs/xhs_after_publish.png")
    result = {
        "status": "pending_confirmation",
        "final_publish_clicked": True,
        "screenshot": str(after),
        "note": "Final publish was tapped, but success still requires manual or SOP verification.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    log.finish(result)


if __name__ == "__main__":
    main()
