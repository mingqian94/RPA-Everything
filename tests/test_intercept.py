"""core.intercept / core.browser.is_logged_in 单元测试（mock page，不开浏览器）。"""

import asyncio
import json

import pytest

from core import intercept
from core.browser import is_logged_in


class FakePage:
    """最小 mock：evaluate 按传入的 JS 片段返回预置数据。"""
    def __init__(self, responses):
        # responses: list of {"url", "body"}
        self._responses = responses
        self.installed = None

    async def add_init_script(self, script):
        self.installed = script

    async def evaluate(self, expr, arg=None):
        # 只区分 collect 用的 .length 计数 和 read 用的 filter 列表
        matched = [r for r in self._responses if arg and arg in r["url"]]
        if ".length" in expr:
            return len(matched)
        return matched


@pytest.mark.unit
def test_install_adds_hook():
    page = FakePage([])
    asyncio.run(intercept.install(page))
    assert page.installed is not None
    assert "__rpa_responses" in page.installed


@pytest.mark.unit
def test_read_parses_matching_json():
    page = FakePage([
        {"url": "https://x.com/api/list?p=1", "body": json.dumps({"items": [1, 2]})},
        {"url": "https://x.com/api/other", "body": "{}"},
        {"url": "https://x.com/api/list?p=2", "body": "not json"},
    ])
    out = asyncio.run(intercept.read(page, "api/list"))
    assert len(out) == 2
    assert out[0]["json"] == {"items": [1, 2]}
    assert out[1]["json"] is None  # 解析失败不抛，返回 None


@pytest.mark.unit
def test_read_filters_by_keyword():
    page = FakePage([
        {"url": "https://x.com/api/list", "body": "{}"},
        {"url": "https://x.com/api/detail", "body": "{}"},
    ])
    out = asyncio.run(intercept.read(page, "detail"))
    assert len(out) == 1 and "detail" in out[0]["url"]


@pytest.mark.unit
def test_collect_returns_when_stable():
    page = FakePage([
        {"url": "https://x.com/api/list", "body": json.dumps({"ok": 1})},
    ])
    out = asyncio.run(intercept.collect(page, "api/list", settle_polls=1, poll_interval=0))
    assert len(out) == 1 and out[0]["json"] == {"ok": 1}


@pytest.mark.unit
def test_collect_times_out_empty():
    page = FakePage([])  # 从不出现匹配
    out = asyncio.run(intercept.collect(page, "never", timeout=0.05, poll_interval=0.01))
    assert out == []


# ── is_logged_in ─────────────────────────────────────────────────────

class FakeContext:
    def __init__(self, cookies):
        self._cookies = cookies

    async def cookies(self, url=None):
        return self._cookies


class FakePageWithContext:
    def __init__(self, cookies):
        self.context = FakeContext(cookies)


@pytest.mark.unit
def test_is_logged_in_true():
    page = FakePageWithContext([{"name": "session_id", "value": "abc"}])
    assert asyncio.run(is_logged_in(page, "session_id")) is True


@pytest.mark.unit
def test_is_logged_in_false_when_missing():
    page = FakePageWithContext([{"name": "other", "value": "x"}])
    assert asyncio.run(is_logged_in(page, "session_id")) is False


@pytest.mark.unit
def test_is_logged_in_false_when_empty_value():
    page = FakePageWithContext([{"name": "session_id", "value": ""}])
    assert asyncio.run(is_logged_in(page, "session_id")) is False
