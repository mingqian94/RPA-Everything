import pytest
from core.config import get


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    """patch get() 实际读取的模块级 config dict，不依赖 config.yaml。"""
    fake = {
        "llm": {"api_key": "sk-test", "model": "claude-haiku"},
        "systems": {"crm": {"url": "https://crm.example.com"}},
        "feishu_project": {"view_url": "https://project.feishu.cn/x", "project_key": "abc123"},
    }
    monkeypatch.setitem(get.__globals__, "config", fake)


def test_get_top_level_nested():
    assert get("llm.api_key") == "sk-test"


def test_get_three_levels():
    assert get("systems.crm.url") == "https://crm.example.com"


def test_get_missing_key_returns_default():
    assert get("missing.key", "fallback") == "fallback"


def test_get_missing_key_returns_none():
    assert get("missing.key") is None


def test_get_partial_path_returns_dict():
    val = get("feishu_project")
    assert isinstance(val, dict)
    assert val["project_key"] == "abc123"
