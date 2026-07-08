import pytest

from showcase.web.xiaohongshu import _common


class FakePage:
    def __init__(self, text):
        self.text = text

    async def evaluate(self, js):
        return self.text


@pytest.mark.unit
def test_xiaohongshu_login_required_detects_search_gate():
    page = FakePage("登录后查看搜索结果\n手机号登录\n获取验证码")

    import asyncio

    assert asyncio.run(_common.is_login_required(page))


@pytest.mark.unit
def test_xiaohongshu_login_required_allows_content():
    page = FakePage("露营攻略 收藏 评论")

    import asyncio

    assert not asyncio.run(_common.is_login_required(page))
