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


def test_security_policy_is_linked_from_agent_docs():
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "External Side Effects" in security
    assert "Prompt Injection" in security
    for filename in ("README.md", "README.zh-CN.md", "AGENTS.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "SECURITY.md" in text


def test_evals_trace_replay_and_android_smoke_are_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "evals/run.py" in readme
    assert "harness/replay" in readme
    assert "showcase/android/smoke_test/smoke_test" in readme


def test_non_developer_onboarding_is_documented():
    for filename in ("README.md", "README.zh-CN.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "setup.ps1" in text
        assert "tools/setup.sh" in text
        assert "harness/doctor" in text
        assert "harness/runtime" in text
        assert "workflow-template.zh-CN.md" in text
