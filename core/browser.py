"""
浏览器控制：通过 CDP 复用用户已登录的 Chrome。

使用前运行启动脚本（只需第一次登录，之后免登录）：
  macOS:   tools/start_chrome.sh
  Windows: tools/start_chrome.bat
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Page, Browser
from core.config import get as _cfg_get

_CDP_URL = _cfg_get("browser.cdp_url") or "http://localhost:9222"

_HINT = """
Chrome 未以调试端口启动，请先运行启动脚本：
  macOS:   sh tools/start_chrome.sh
  Windows: tools\\start_chrome.bat

首次运行需登录各系统，之后免登录直接使用。
"""


class BrowserManager:
    _browser: Browser | None = None
    _playwright = None

    @classmethod
    async def _connect(cls):
        if cls._playwright is None:
            cls._playwright = await async_playwright().start()
        try:
            cls._browser = await cls._playwright.chromium.connect_over_cdp(_CDP_URL)
        except Exception:
            raise RuntimeError(_HINT)

    @classmethod
    async def new_page(cls) -> Page:
        if cls._browser is None:
            await cls._connect()
        context = cls._browser.contexts[0]
        return await context.new_page()

    @classmethod
    async def close(cls):
        if cls._playwright:
            await cls._playwright.stop()
            cls._browser = None
            cls._playwright = None


async def is_login_page(page: Page) -> bool:
    """截图后问 LLM 当前是否是登录 / 认证页面。"""
    import tempfile
    from core.llm import decide
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    await page.screenshot(path=tmp.name)
    answer = decide(
        "这张截图显示的是一个需要用户输入账号密码或扫码登录的认证页面吗？只回答「是」或「否」。",
        screenshot_path=tmp.name,
    )
    return answer.strip().startswith("是")


@asynccontextmanager
async def open_page(url: str | None = None):
    """打开页面，用完自动关闭。Chrome 未就绪时给出友好提示。"""
    page = await BrowserManager.new_page()
    try:
        if url:
            await page.goto(url)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
        yield page
    finally:
        await page.close()
