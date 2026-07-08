"""Crawl posts from a Xiaohongshu user profile."""

from __future__ import annotations

import argparse
import sys

from core.browser import open_page
from core.logger import SkillLogger

from ._common import argv_after_separator, collect_note_cards, goto_and_settle, is_login_required, slow_scroll, user_url, write_json


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
        try:
            await goto_and_settle(page, target)
        except Exception as exc:
            result = {
                "source": "user",
                "url": target,
                "error": "navigation_failed",
                "detail": f"{exc.__class__.__name__}: {str(exc)[:500]}",
                "login_required": None,
                "count": 0,
                "posts": [],
            }
            write_json(result, args.output, "web/xiaohongshu/user_posts")
            log.finish(result)
            return result
        log.step(f"Opened user page: {target}")
        if await is_login_required(page):
            result = {"source": "user", "url": target, "login_required": True, "count": 0, "posts": []}
            write_json(result, args.output, "web/xiaohongshu/user_posts")
            log.finish(result)
            return result
        await slow_scroll(page, args.scroll_rounds)
        posts = await collect_note_cards(page, args.limit)

    result = {"source": "user", "url": target, "login_required": False, "count": len(posts), "posts": posts}
    write_json(result, args.output, "web/xiaohongshu/user_posts")
    log.finish(result)
    return result


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
