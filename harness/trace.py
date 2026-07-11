"""Trace JSON export and replay helpers for Harness runs."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from core.redact import redact


def export_trace_json(goal: str, results: list[dict], output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "version": 1,
        "goal": redact(goal),
        "results": redact(results),
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_trace(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError("Trace JSON must be an object with a results field.")
    return data


def iter_tool_calls(trace_record: dict[str, Any]):
    for result in trace_record.get("results", []):
        for item in result.get("trace", []):
            if item.get("is_error"):
                continue
            tool = item.get("tool")
            if not tool or tool in {"browser_screenshot", "android_screenshot", "desktop_screenshot", "android_dump_ui"}:
                continue
            yield result, item


async def replay_trace(trace_record: dict[str, Any], dry_run: bool = False) -> list[dict]:
    """Replay supported tool calls. Dry-run returns the planned replay sequence."""
    replayed: list[dict] = []
    page_ctx = None
    page = None
    android = None

    try:
        for _, item in iter_tool_calls(trace_record):
            tool = item["tool"]
            args = item.get("args", {})
            replayed.append({"tool": tool, "args": args})
            if dry_run:
                continue

            if tool.startswith("browser_"):
                from core.browser import open_page

                if tool == "browser_navigate":
                    if page_ctx is not None:
                        await page_ctx.__aexit__(None, None, None)
                    page_ctx = open_page(args.get("url") or None)
                    page = await page_ctx.__aenter__()
                    continue
                if page is None:
                    page_ctx = open_page(None)
                    page = await page_ctx.__aenter__()
                if tool == "browser_click":
                    if args.get("selector"):
                        await page.click(args["selector"])
                    elif args.get("text"):
                        await page.click(f"text={args['text']}")
                elif tool == "browser_type":
                    await page.fill(args.get("selector", ""), args.get("text", ""))
                elif tool == "browser_evaluate":
                    await page.evaluate(args.get("js", ""))
                continue

            if tool.startswith("android_"):
                if android is None:
                    from core.android import AndroidDevice

                    android = AndroidDevice(serial=args.get("serial"))
                if tool == "android_tap":
                    if "rx" in args and "ry" in args:
                        android.tap_ratio(float(args["rx"]), float(args["ry"]))
                    else:
                        android.tap(int(args.get("x", 0)), int(args.get("y", 0)))
                elif tool == "android_tap_element":
                    android.tap_ui_node(
                        text=args.get("text", ""),
                        resource_id=args.get("resource_id", ""),
                        content_desc=args.get("content_desc", ""),
                        exact=bool(args.get("exact", False)),
                    )
                elif tool == "android_swipe":
                    if all(k in args for k in ("rx1", "ry1", "rx2", "ry2")):
                        android.swipe_ratio(
                            float(args["rx1"]), float(args["ry1"]),
                            float(args["rx2"]), float(args["ry2"]),
                            int(args.get("duration_ms", 300)),
                        )
                    else:
                        android.swipe(
                            int(args.get("x1", 0)), int(args.get("y1", 0)),
                            int(args.get("x2", 0)), int(args.get("y2", 0)),
                            int(args.get("duration_ms", 300)),
                        )
                elif tool == "android_key":
                    android.key(args.get("keycode", ""))
                elif tool == "android_type":
                    android.input_text(
                        args.get("text", ""),
                        unicode=bool(args.get("unicode", False)),
                        restore_ime=bool(args.get("restore_ime", True)),
                    )
                continue

            if tool.startswith("desktop_"):
                from core.desktop import click, hotkey, type_text

                if tool == "desktop_click":
                    click(int(args.get("x", 0)), int(args.get("y", 0)))
                elif tool == "desktop_type":
                    type_text(args.get("text", ""))
                elif tool == "desktop_hotkey":
                    hotkey(*args.get("keys", []))
    finally:
        if page_ctx is not None:
            await page_ctx.__aexit__(None, None, None)

    return replayed


def replay_trace_sync(trace_record: dict[str, Any], dry_run: bool = False) -> list[dict]:
    return asyncio.run(replay_trace(trace_record, dry_run=dry_run))
