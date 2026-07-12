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
        "showcase/web/xhs/user_posts",
        "showcase/web/xhs/search_posts",
        "showcase/web/xhs/post_detail",
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
    assert "showcase/mobile/android/smoke_test/smoke_test" in readme


def test_non_developer_onboarding_is_documented():
    for filename in ("README.md", "README.zh-CN.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "setup.ps1" in text
        assert "tools/setup.sh" in text
        assert "harness/doctor" in text
        assert "harness/runtime" in text
        assert "workflow-template.zh-CN.md" in text


def test_agent_bootstrap_and_supervised_run_are_documented():
    for filename in ("README.md", "README.zh-CN.md", "QUICKSTART.zh-CN.md", "AGENTS.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "agent-bootstrap" in text
        assert "harness/demo" in text
        assert "harness/supervise" in text

    assert (ROOT / "docs" / "agent-bootstrap.zh-CN.md").exists()
    assert (ROOT / "docs" / "supervised-run.zh-CN.md").exists()


def test_app_routes_distinguish_direct_integrations_from_desktop_fallbacks():
    text = (ROOT / "showcase" / "app" / "README.md").read_text(encoding="utf-8")
    integration = (ROOT / "showcase" / "app" / "integration" / "README.md").read_text(encoding="utf-8")

    assert "integration/" in text
    assert "desktop/" in text
    assert "视觉识别" in text
    assert "MCP Server、CLI 或 API" in integration
