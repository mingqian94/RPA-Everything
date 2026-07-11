"""Crawl text, media, and visible engagement from a Xiaohongshu post."""

from __future__ import annotations

import argparse
import sys

from core.browser import open_page
from core.logger import SkillLogger

from ._common import argv_after_separator, collect_post_detail, goto_and_settle, human_pause, is_login_required, write_json


async def main():
    parser = argparse.ArgumentParser(description="Crawl Xiaohongshu post detail")
    parser.add_argument("--url", required=True, help="Xiaohongshu post URL.")
    parser.add_argument("--output", default="", help="Output JSON path. Prints JSON when omitted.")
    args = parser.parse_args(argv_after_separator(sys.argv))

    log = SkillLogger("web/xiaohongshu/post_detail")
    async with open_page() as page:
        try:
            await goto_and_settle(page, args.url)
        except Exception as exc:
            detail = {
                "url": args.url,
                "error": "navigation_failed",
                "detail": f"{exc.__class__.__name__}: {str(exc)[:500]}",
                "login_required": None,
                "text": "",
                "images": [],
                "videos": [],
                "engagement": {},
            }
            write_json(detail, args.output, "web/xiaohongshu/post_detail")
            log.finish({"url": args.url, "error": "navigation_failed"})
            return detail
        log.step(f"Opened post: {args.url}")
        if await is_login_required(page):
            detail = {"url": args.url, "login_required": True, "text": "", "images": [], "videos": [], "engagement": {}}
            write_json(detail, args.output, "web/xiaohongshu/post_detail")
            log.finish({"url": args.url, "login_required": True})
            return detail
        await human_pause(2.0, 4.0)
        detail = await collect_post_detail(page)
        detail["login_required"] = False

    write_json(detail, args.output, "web/xiaohongshu/post_detail")
    log.finish({"url": args.url, "images": len(detail.get("images", [])), "videos": len(detail.get("videos", []))})
    return detail


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
