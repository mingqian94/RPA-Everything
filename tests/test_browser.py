"""
Browser 测试：需要 Chrome 以调试端口启动。
未启动时自动 skip（conftest.py 处理）。

运行前：sh tools/start_chrome.sh
运行：  pytest -m browser
"""
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


def test_extract_table_local_html(tmp_path):
    """extract_table 能从 HTML 表格提取数据，返回 JSON。
    用本地文件而非公开 URL——外网在 CI/部分网络环境不可达，测试会白挂。"""
    html = tmp_path / "table.html"
    html.write_text(
        "<html><body><table>"
        "<tr><th>Company</th><th>Price</th></tr>"
        "<tr><td>Acme</td><td>100</td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "run.py", "showcase/web/extract_table",
         "--", "--url", html.as_uri()],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT), timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = result.stdout
    assert "Acme" in output and "Company" in output, f"意外输出：{output[:200]}"
