"""Shared helpers for Xiaohongshu web showcases."""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import Page

XHS_HOST = "https://www.xiaohongshu.com"


def search_url(keyword: str) -> str:
    return f"{XHS_HOST}/search_result?keyword={quote(keyword)}"


def user_url(user_id: str) -> str:
    return f"{XHS_HOST}/user/profile/{quote(user_id)}"


async def human_pause(min_wait: float = 1.2, max_wait: float = 3.2) -> None:
    await asyncio.sleep(random.uniform(min_wait, max_wait))


async def slow_scroll(page: Page, rounds: int, min_wait: float = 1.4, max_wait: float = 3.8) -> None:
    for _ in range(max(0, rounds)):
        await page.mouse.wheel(0, random.randint(520, 980))
        await human_pause(min_wait, max_wait)


async def goto_and_settle(page: Page, url: str) -> None:
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await human_pause(2.0, 4.0)
    try:
        await page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:
        pass


async def collect_note_cards(page: Page, limit: int) -> list[dict]:
    """Collect visible note links and card text using conservative DOM heuristics."""
    return await page.evaluate(
        """
        (limit) => {
          const seen = new Set();
          const out = [];
          const anchors = Array.from(document.querySelectorAll('a[href]'));
          for (const a of anchors) {
            let href = a.href || '';
            if (!href || !/xiaohongshu\\.com\\/(explore|discovery\\/item)\\//.test(href)) continue;
            href = href.split('?')[0];
            if (seen.has(href)) continue;
            seen.add(href);
            const card = a.closest('section, article, div') || a;
            const text = (card.innerText || a.innerText || '').trim().replace(/\\s+/g, ' ');
            const img = card.querySelector('img');
            out.push({
              url: href,
              title: text.slice(0, 160),
              text: text.slice(0, 500),
              cover: img ? (img.currentSrc || img.src || '') : ''
            });
            if (out.length >= limit) break;
          }
          return out;
        }
        """,
        limit,
    )


async def collect_post_detail(page: Page) -> dict:
    """Collect visible text/media from a note detail page."""
    return await page.evaluate(
        """
        () => {
          const clean = (s) => (s || '').trim().replace(/\\s+/g, ' ');
          const uniq = (items) => Array.from(new Set(items.filter(Boolean)));
          const text = clean(document.body ? document.body.innerText : '');

          const images = uniq(Array.from(document.images).map(img => img.currentSrc || img.src || ''))
            .filter(src => !src.startsWith('data:'));
          const videos = uniq(Array.from(document.querySelectorAll('video')).flatMap(v => {
            const direct = v.currentSrc || v.src || '';
            const sources = Array.from(v.querySelectorAll('source')).map(s => s.src || '');
            return [direct, ...sources];
          }));

          const engagement = {};
          const patterns = [
            ['likes', /(点赞|赞)\\s*([0-9.万wWkK]+)/],
            ['collects', /(收藏)\\s*([0-9.万wWkK]+)/],
            ['comments', /(评论)\\s*([0-9.万wWkK]+)/],
            ['shares', /(分享)\\s*([0-9.万wWkK]+)/]
          ];
          for (const [key, re] of patterns) {
            const m = text.match(re);
            if (m) engagement[key] = m[2];
          }

          return {
            url: location.href,
            title: clean(document.title),
            text,
            images,
            videos,
            engagement
          };
        }
        """
    )


def write_json(data, output: str) -> None:
    if not output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved to {path.resolve()}")


def argv_after_separator(sys_argv: list[str]) -> list[str]:
    try:
        sep = sys_argv.index("--")
        return sys_argv[sep + 1:]
    except ValueError:
        return sys_argv[1:]
