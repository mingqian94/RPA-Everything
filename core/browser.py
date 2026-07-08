"""
浏览器控制：通过 CDP 复用用户已登录的 Chrome。

使用前运行启动脚本（只需第一次登录，之后免登录）：
  macOS:   tools/start_chrome.sh
  Windows: tools/start_chrome.bat
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Page, Browser
from core.config import get as _cfg_get

def _cdp_url() -> str:
    # Prefer IPv4 loopback. On Windows, Playwright may resolve localhost to
    # ::1 while Chrome's debugging port listens only on 127.0.0.1.
    return _cfg_get("browser.cdp_url") or "http://127.0.0.1:9222"

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
            # 加超时：websocket 能连上、但 Chrome 里有卡死的标签页时，
            # connect_over_cdp 枚举页面会一直挂着（默认 180s）。快速失败更好排查。
            cls._browser = await cls._playwright.chromium.connect_over_cdp(
                _cdp_url(), timeout=20000
            )
        except Exception as e:
            raise RuntimeError(f"{_HINT}\n（原始错误：{type(e).__name__}: {e}）") from e

    @classmethod
    async def _ensure_connected(cls):
        """Chrome 重启后旧连接会失效，这里检测并自动重连，
        避免长驻进程（如 MCP server）拿着死连接一直失败。"""
        if cls._browser is None or not cls._browser.is_connected():
            await cls._connect()

    @classmethod
    async def new_page(cls) -> Page:
        await cls._ensure_connected()
        context = cls._browser.contexts[0]
        return await context.new_page()

    @classmethod
    async def current_page(cls) -> Page:
        """返回当前活动标签页（没有则新建）。供 MCP 等长驻调用方复用用户正在看的页面。"""
        await cls._ensure_connected()
        context = cls._browser.contexts[0]
        if context.pages:
            return context.pages[0]
        return await context.new_page()

    @classmethod
    async def close(cls):
        if cls._playwright:
            await cls._playwright.stop()
            cls._browser = None
            cls._playwright = None


async def is_logged_in(page: Page, cookie_name: str, url: str | None = None) -> bool:
    """Whether a (possibly httpOnly) session cookie is present.
    是否存在指定的（可能是 httpOnly 的）会话 cookie。

    Read cookies from the browser via ``context.cookies()`` rather than JS
    ``document.cookie`` — login/session cookies are usually httpOnly and hidden
    from JS, so a document.cookie check would report a logged-in user as logged out.
    通过 ``context.cookies()`` 从浏览器层读取，而不是 JS 的 ``document.cookie``——
    登录/会话 cookie 通常是 httpOnly、对 JS 不可见，用 document.cookie 会把已登录误判成未登录。

    ``url`` optionally scopes the cookie lookup to one origin (e.g. "https://x.com").
    ``url`` 可选，把 cookie 查询限定到某个源。"""
    cookies = await (page.context.cookies(url) if url else page.context.cookies())
    return any(c.get("name") == cookie_name and c.get("value") for c in cookies)


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
