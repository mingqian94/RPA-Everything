"""
Network response interception for pages that load data via background API calls.
后台 API 加载数据的页面：拦截其网络响应。

Many web apps render nothing useful in the initial HTML — the data arrives via
`fetch` / `XMLHttpRequest` after load. Instead of scraping the DOM, hook both
request mechanisms in page context, let the page make its own (already
authenticated / signed) requests, and read the responses back.
很多页面初始 HTML 里没有有用数据，数据是加载后经 `fetch` / `XMLHttpRequest` 到达的。
与其抓 DOM，不如在页面上下文里 hook 这两种请求，让页面自己发（已带鉴权/签名的）
请求，我们把响应读回来。

Business-agnostic: this module only captures raw responses by URL substring;
parsing the payload is the caller's job.
与业务无关：本模块只按 URL 子串捕获原始响应，如何解析由调用方决定。

Usage / 用法::

    from core import intercept

    await intercept.install(page)            # before navigation / 导航前安装
    await page.goto(url)
    responses = await intercept.collect(page, "api/list")  # poll until stable
    for r in responses:
        data = r["json"]                     # parsed JSON (or None) / 已解析的 JSON
"""

from __future__ import annotations

import asyncio
import json as _json

# Injected into page context. Wraps fetch + XMLHttpRequest so every response
# body is stashed on window.__rpa_responses as {url, body}.
# 注入页面上下文：包裹 fetch + XMLHttpRequest，把每个响应体存到
# window.__rpa_responses（{url, body}）。
HOOK_JS = """
() => {
    if (window.__rpa_hooked) return;
    window.__rpa_hooked = true;
    window.__rpa_responses = [];

    const record = (url, text) => {
        try { window.__rpa_responses.push({url: String(url), body: text}); } catch (e) {}
    };

    const _fetch = window.fetch;
    window.fetch = async function(...args) {
        const url = (typeof args[0] === 'string') ? args[0] : (args[0] && args[0].url) || '';
        const resp = await _fetch.apply(this, args);
        try { resp.clone().text().then(t => record(url, t)).catch(() => {}); } catch (e) {}
        return resp;
    };

    const _open = XMLHttpRequest.prototype.open;
    const _send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this.__rpa_url = url;
        return _open.call(this, method, url, ...rest);
    };
    XMLHttpRequest.prototype.send = function(...args) {
        this.addEventListener('load', () => {
            if (this.responseType === '' || this.responseType === 'text') {
                record(this.__rpa_url, this.responseText);
            }
        });
        return _send.apply(this, args);
    };
}
"""


async def install(page) -> None:
    """Install the response hook. Must be called BEFORE navigating the page,
    so the hook is present when the page fires its requests.
    安装响应 hook。必须在页面导航之前调用，否则页面发请求时 hook 还没装上。"""
    await page.add_init_script(HOOK_JS)


async def read(page, url_keyword: str) -> list[dict]:
    """Return intercepted responses whose URL contains `url_keyword`, as
    ``[{"url": str, "json": parsed-or-None}]``. Safe to call repeatedly (e.g.
    after each scroll) to pick up lazily loaded pages.
    返回 URL 含 `url_keyword` 的已拦截响应，格式 ``[{"url", "json"}]``（json 解析失败为 None）。
    可重复调用（如每次滚动后），以收取懒加载的分页。"""
    raw = await page.evaluate(
        "(kw) => (window.__rpa_responses || []).filter(r => r.url.includes(kw))",
        url_keyword,
    )
    out = []
    for r in raw:
        try:
            parsed = _json.loads(r["body"])
        except (ValueError, TypeError, KeyError):
            parsed = None
        out.append({"url": r.get("url", ""), "json": parsed})
    return out


async def collect(
    page,
    url_keyword: str,
    *,
    timeout: float = 20.0,
    settle_polls: int = 3,
    poll_interval: float = 0.5,
) -> list[dict]:
    """Poll intercepted responses until the match count stays stable (non-zero
    and unchanged for `settle_polls` polls) or `timeout` elapses, then return
    them via :func:`read`. Robust to slow/fast networks — no fixed sleeps.
    轮询已拦截响应，直到匹配数量稳定（非零且连续 `settle_polls` 次不变）或超时，
    再经 :func:`read` 返回。对快慢网络都稳，不用写死 sleep。

    Assumes :func:`install` was called and the page has been navigated.
    前提：已调用 :func:`install` 且页面已导航。"""
    deadline = asyncio.get_event_loop().time() + timeout
    prev, stable = -1, 0
    while asyncio.get_event_loop().time() < deadline:
        count = await page.evaluate(
            "(kw) => (window.__rpa_responses || []).filter(r => r.url.includes(kw)).length",
            url_keyword,
        )
        if count > 0 and count == prev:
            stable += 1
            if stable >= settle_polls:
                break
        else:
            stable = 0
        prev = count
        await asyncio.sleep(poll_interval)
    return await read(page, url_keyword)
