"""Crawl text, media, and visible engagement from a Xiaohongshu post."""

from __future__ import annotations

import argparse
import sys

from core.browser import open_page
from core.logger import SkillLogger

from ._common import argv_after_separator, collect_post_detail, goto_and_settle, human_pause, write_json


async def main():
    parser = argparse.ArgumentParser(description="Crawl Xiaohongshu post detail")
    parser.add_argument("--url", required=True, help="Xiaohongshu post URL.")
    parser.add_argument("--output", default="", help="Output JSON path. Prints JSON when omitted.")
    args = parser.parse_args(argv_after_separator(sys.argv))

    log = SkillLogger("web/xiaohongshu/post_detail")
    async with open_page() as page:
        await goto_and_settle(page, args.url)
        log.step(f"Opened post: {args.url}")
        await human_pause(2.0, 4.0)
        detail = await collect_post_detail(page)

    write_json(detail, args.output)
    log.finish({"url": args.url, "images": len(detail.get("images", [])), "videos": len(detail.get("videos", []))})
    return detail


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
