"""Crawl posts from a Xiaohongshu user profile."""

from __future__ import annotations

import argparse
import sys

from core.browser import open_page
from core.logger import SkillLogger

from ._common import argv_after_separator, collect_note_cards, goto_and_settle, slow_scroll, user_url, write_json


async def main():
    parser = argparse.ArgumentParser(description="Crawl Xiaohongshu user posts")
    parser.add_argument("--user-url", default="", help="Full Xiaohongshu user profile URL.")
    parser.add_argument("--user-id", default="", help="User id; used when --user-url is not provided.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum notes to collect.")
    parser.add_argument("--scroll-rounds", type=int, default=8, help="Slow scroll rounds.")
    parser.add_argument("--output", default="", help="Output JSON path. Prints JSON when omitted.")
    args = parser.parse_args(argv_after_separator(sys.argv))

    if not args.user_url and not args.user_id:
        parser.error("Either --user-url or --user-id is required")

    target = args.user_url or user_url(args.user_id)
    log = SkillLogger("web/xiaohongshu/user_posts")

    async with open_page() as page:
        await goto_and_settle(page, target)
        log.step(f"Opened user page: {target}")
        await slow_scroll(page, args.scroll_rounds)
        posts = await collect_note_cards(page, args.limit)

    result = {"source": "user", "url": target, "count": len(posts), "posts": posts}
    write_json(result, args.output)
    log.finish(result)
    return result


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
