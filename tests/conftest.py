import pytest
import requests


def _chrome_available() -> bool:
    try:
        r = requests.get("http://localhost:9222/json", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def pytest_collection_modifyitems(items):
    """Browser 测试：Chrome 未启动时自动 skip，无需手动指定。"""
    if _chrome_available():
        return
    skip = pytest.mark.skip(reason="Chrome 未启动，运行 `sh tools/start_chrome.sh` 后重试")
    for item in items:
        if item.get_closest_marker("browser"):
            item.add_marker(skip)
