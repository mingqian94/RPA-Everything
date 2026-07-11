"""Crawl posts from a Xiaohongshu search keyword or tag."""

from __future__ import annotations

import argparse
import sys

from core.browser import open_page
from core.logger import SkillLogger

from ._common import argv_after_separator, collect_note_cards, goto_and_settle, is_login_required, search_url, slow_scroll, write_json


async def main():
    parser = argparse.ArgumentParser(description="Crawl Xiaohongshu search/tag posts")
    parser.add_argument("--keyword", required=True, help="Search keyword or tag, for example 露营 or #露营装备.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum notes to collect.")
    parser.add_argument("--scroll-rounds", type=int, default=8, help="Slow scroll rounds.")
    parser.add_argument("--output", default="", help="Output JSON path. Prints JSON when omitted.")
    args = parser.parse_args(argv_after_separator(sys.argv))

    target = search_url(args.keyword)
    log = SkillLogger("web/xiaohongshu/search_posts")

    async with open_page() as page:
        try:
            await goto_and_settle(page, target)
        except Exception as exc:
            result = {
                "source": "search",
                "keyword": args.keyword,
                "url": target,
                "error": "navigation_failed",
                "detail": f"{exc.__class__.__name__}: {str(exc)[:500]}",
                "login_required": None,
                "count": 0,
                "posts": [],
            }
            write_json(result, args.output, "web/xiaohongshu/search_posts")
            log.finish(result)
            return result
        log.step(f"Opened search page: {args.keyword}")
        if await is_login_required(page):
            result = {
                "source": "search",
                "keyword": args.keyword,
                "url": target,
                "login_required": True,
                "count": 0,
                "posts": [],
            }
            write_json(result, args.output, "web/xiaohongshu/search_posts")
            log.finish(result)
            return result
        await slow_scroll(page, args.scroll_rounds)
        posts = await collect_note_cards(page, args.limit)

    result = {"source": "search", "keyword": args.keyword, "url": target, "login_required": False, "count": len(posts), "posts": posts}
    write_json(result, args.output, "web/xiaohongshu/search_posts")
    log.finish(result)
    return result


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
