"""connectors/feishu.py 消息封装的单元测试（mock 网络请求）。"""

import json

import pytest

from connectors import feishu


@pytest.fixture(autouse=True)
def fake_token(monkeypatch):
    """跳过真实 token 请求。"""
    import time
    monkeypatch.setitem(feishu._token_cache, "token", "t-fake")
    monkeypatch.setitem(feishu._token_cache, "expires_at", time.time() + 3600)


@pytest.mark.unit
def test_send_content_is_valid_json(monkeypatch):
    captured = {}

    class FakeResp:
        def json(self):
            return {"code": 0}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return FakeResp()

    monkeypatch.setattr(feishu.requests, "post", fake_post)

    # 含引号和换行的消息不能打穿 JSON
    assert feishu.send("ou_x", 'he said "hi"\nline2') is True
    content = captured["json"]["content"]
    assert json.loads(content) == {"text": 'he said "hi"\nline2'}


@pytest.mark.unit
def test_send_has_timeout(monkeypatch):
    captured = {}

    class FakeResp:
        def json(self):
            return {"code": 0}

    monkeypatch.setattr(feishu.requests, "post", lambda url, **kw: captured.update(kw) or FakeResp())
    feishu.send("ou_x", "hello")
    assert captured.get("timeout")
