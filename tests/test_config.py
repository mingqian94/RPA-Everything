import pytest
from core.config import get


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    """patch get() 实际读取的模块级 config dict，不依赖 config.yaml。"""
    fake = {
        "llm": {"api_key": "sk-test", "model": "claude-haiku"},
        "systems": {"crm": {"url": "https://crm.example.com"}},
        "feishu_project": {"view_url": "https://project.feishu.cn/x", "project_key": "abc123"},
        "flags": {"enabled": False, "count": 0, "name": ""},
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


def test_get_explicit_falsy_values_not_swallowed():
    """显式配置的 False/0/空串必须原样返回，不能被 default 覆盖。"""
    assert get("flags.enabled", True) is False
    assert get("flags.count", 99) == 0
    assert get("flags.name", "fallback") == ""


def test_get_env_fallback(monkeypatch):
    monkeypatch.setenv("MISSING_KEY", "from-env")
    assert get("missing.key") == "from-env"


def test_get_config_wins_over_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "from-env")
    assert get("llm.api_key") == "sk-test"
