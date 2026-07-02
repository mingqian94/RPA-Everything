"""
Browser 测试：需要 Chrome 以调试端口启动。
未启动时自动 skip（conftest.py 处理）。

运行前：sh tools/start_chrome.sh
运行：  pytest -m browser
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import requests

pytestmark = pytest.mark.browser

ROOT = Path(__file__).parent.parent


def test_chrome_cdp_reachable():
    """Chrome CDP 端口可连接，且至少有一个页面。"""
    r = requests.get("http://localhost:9222/json", timeout=5)
    assert r.status_code == 200
    pages = r.json()
    assert isinstance(pages, list) and len(pages) > 0


def test_extract_table_public_url():
    """extract_table 能从公开 URL 提取 HTML 表格，返回 JSON。"""
    result = subprocess.run(
        [sys.executable, "run.py", "showcase/web/extract_table",
         "--", "--url", "https://www.w3schools.com/html/html_tables.asp"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # 输出里应包含 JSON 数组（表格行）
    output = result.stdout
    assert "[" in output or "Company" in output, f"意外输出：{output[:200]}"
