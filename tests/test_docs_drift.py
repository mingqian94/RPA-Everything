"""Static checks that keep public docs aligned with callable framework entrypoints."""

import re

import mcp_server
from core.skills import ROOT


def test_agents_tool_count_matches_mcp_server():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    match = re.search(r"连接后可用工具（(\d+) 个）", text)
    assert match, "AGENTS.md should document the MCP tool count."

    assert int(match.group(1)) == len(mcp_server.ALL_TOOLS)


def test_harness_trace_export_is_documented():
    for filename in ("README.md", "README.zh-CN.md", "AGENTS.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "--export-trace" in text


def test_xiaohongshu_showcase_tools_are_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for skill in (
        "showcase/web/xiaohongshu/user_posts",
        "showcase/web/xiaohongshu/search_posts",
        "showcase/web/xiaohongshu/post_detail",
    ):
        assert skill in readme
