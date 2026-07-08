"""mcp_server 的纯逻辑单元测试（不启动 server、不连浏览器）。"""

import pytest

import mcp_server


@pytest.mark.unit
class TestSafeSkillPath:
    def test_normal_name(self):
        path = mcp_server.safe_skill_path("my_skill")
        assert path is not None
        assert path.name == "my_skill.py"
        assert "skills" in path.parts

    def test_subdirectory(self):
        path = mcp_server.safe_skill_path("crm/export_students")
        assert path is not None
        assert path.parent.name == "crm"

    def test_path_traversal_rejected(self):
        assert mcp_server.safe_skill_path("../evil") is None
        assert mcp_server.safe_skill_path("../../outside/evil") is None

    def test_absolute_path_rejected(self):
        assert mcp_server.safe_skill_path("C:/Windows/evil") is None or \
            mcp_server.safe_skill_path("/etc/evil") is None


@pytest.mark.unit
def test_tool_names_unique():
    """共享工具 + MCP 特有工具不能重名（task_complete 已被过滤）。"""
    names = [t["name"] for t in mcp_server.ALL_TOOLS]
    assert len(names) == len(set(names))
    assert "task_complete" not in names


@pytest.mark.unit
def test_every_mcp_only_tool_has_handler():
    for t in mcp_server._MCP_ONLY_TOOLS:
        assert t["name"] in mcp_server._HANDLERS


@pytest.mark.unit
def test_orchestrate_exposes_confirm_external():
    orchestrate = next(t for t in mcp_server._MCP_ONLY_TOOLS if t["name"] == "orchestrate")
    assert "confirm_external" in orchestrate["input_schema"]["properties"]


@pytest.mark.unit
def test_orchestrate_exposes_export_trace():
    orchestrate = next(t for t in mcp_server._MCP_ONLY_TOOLS if t["name"] == "orchestrate")
    assert "export_trace" in orchestrate["input_schema"]["properties"]
