"""core/agent.py agentic loop 的单元测试（mock LLM 调用，不联网、不开浏览器）。"""

import asyncio

import pytest

from core import agent as agent_mod


class FakeBlock:
    def __init__(self, type_, name=None, input_=None, text=None):
        self.type = type_
        self.name = name
        self.input = input_ or {}
        self.id = "toolu_fake"
        if text is not None:
            self.text = text


class FakeResp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


def _patch_llm(monkeypatch, responses: list[FakeResp]):
    """让 agent_step 按序返回预置响应。"""
    it = iter(responses)

    def fake_step(messages, tools, system="", tool_choice=None):
        return next(it)

    monkeypatch.setattr(agent_mod, "agent_step", fake_step)


@pytest.mark.unit
def test_task_complete_returns_ok(monkeypatch):
    _patch_llm(monkeypatch, [
        FakeResp("tool_use", [FakeBlock("tool_use", "task_complete", {"result": "搞定"})]),
    ])
    result = asyncio.run(agent_mod.run_browser("目标", page=None))
    assert result == {"status": "ok", "result": "搞定"}


@pytest.mark.unit
def test_end_turn_returns_text(monkeypatch):
    _patch_llm(monkeypatch, [
        FakeResp("end_turn", [FakeBlock("text", text="直接回答")]),
    ])
    result = asyncio.run(agent_mod.run_desktop("目标"))
    assert result["status"] == "ok"
    assert result["result"] == "直接回答"


@pytest.mark.unit
def test_unexpected_stop_reason_is_error(monkeypatch):
    _patch_llm(monkeypatch, [FakeResp("max_tokens", [])])
    result = asyncio.run(agent_mod.run_browser("目标", page=None))
    assert result["status"] == "error"
    assert "max_tokens" in result["error"]


@pytest.mark.unit
def test_screenshot_loop_guard(monkeypatch):
    """连续 5 次截图必须触发盲循环保护，而不是耗尽 MAX_STEPS。"""
    async def fake_exec(name, args, page):
        return [{"type": "text", "text": "截图完成。"}]

    monkeypatch.setattr(agent_mod, "execute_browser_tool", fake_exec)
    def shot():
        return FakeResp("tool_use", [FakeBlock("tool_use", "browser_screenshot", {})])
    _patch_llm(monkeypatch, [shot() for _ in range(6)])

    result = asyncio.run(agent_mod.run_browser("目标", page=None))
    assert result["status"] == "error"
    assert "截图循环" in result["error"]


@pytest.mark.unit
def test_tool_error_fed_back_and_loop_continues(monkeypatch):
    """工具抛异常应作为 is_error 的 tool_result 反馈给模型，循环继续。"""
    async def fake_exec(name, args, page):
        raise RuntimeError("元素不存在")

    monkeypatch.setattr(agent_mod, "execute_browser_tool", fake_exec)
    _patch_llm(monkeypatch, [
        FakeResp("tool_use", [FakeBlock("tool_use", "browser_click", {"text": "导出"})]),
        FakeResp("tool_use", [FakeBlock("tool_use", "task_complete", {"result": "改用其他方式完成"})]),
    ])
    result = asyncio.run(agent_mod.run_browser("目标", page=None))
    assert result["status"] == "ok"


@pytest.mark.unit
def test_max_steps_exceeded(monkeypatch):
    async def fake_exec(name, args, page):
        return [{"type": "text", "text": "点击完成。"}]

    monkeypatch.setattr(agent_mod, "execute_browser_tool", fake_exec)
    def click():
        return FakeResp("tool_use", [FakeBlock("tool_use", "browser_click", {"text": "下一页"})])
    _patch_llm(monkeypatch, [click() for _ in range(agent_mod.MAX_STEPS + 1)])

    result = asyncio.run(agent_mod.run_browser("目标", page=None))
    assert result["status"] == "error"
    assert "最大步数" in result["error"]
