"""harness plan() 的单元测试（mock LLM，验证结构化输出解析）。"""

import pytest

from harness import agent as harness


class FakeBlock:
    def __init__(self, type_, name=None, input_=None):
        self.type = type_
        self.name = name
        self.input = input_ or {}


class FakeResp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


@pytest.mark.unit
def test_plan_returns_tasks(monkeypatch):
    tasks = [
        {"skill": "extract_table", "goal": "打开 X 提取表格", "parallel": False, "label": "提取"},
    ]
    monkeypatch.setattr(
        harness, "agent_step",
        lambda messages, tools, system="", tool_choice=None: FakeResp(
            "tool_use", [FakeBlock("tool_use", "submit_plan", {"tasks": tasks})]
        ),
    )
    assert harness.plan("提取表格") == tasks


@pytest.mark.unit
def test_plan_forces_submit_plan_tool(monkeypatch):
    """必须以强制 tool_choice 调用，保证结构化输出。"""
    captured = {}

    def fake_step(messages, tools, system="", tool_choice=None):
        captured["tool_choice"] = tool_choice
        return FakeResp("tool_use", [FakeBlock("tool_use", "submit_plan", {"tasks": [{"skill": "x", "goal": "y", "label": "z"}]})])

    monkeypatch.setattr(harness, "agent_step", fake_step)
    harness.plan("目标")
    assert captured["tool_choice"] == {"type": "tool", "name": "submit_plan"}


@pytest.mark.unit
def test_plan_empty_tasks_raises(monkeypatch):
    monkeypatch.setattr(
        harness, "agent_step",
        lambda messages, tools, system="", tool_choice=None: FakeResp(
            "tool_use", [FakeBlock("tool_use", "submit_plan", {"tasks": []})]
        ),
    )
    with pytest.raises(ValueError, match="规划失败"):
        harness.plan("目标")
