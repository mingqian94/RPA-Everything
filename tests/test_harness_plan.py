"""harness plan() 的单元测试（mock LLM，验证结构化输出解析）。"""

import asyncio
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
def test_plan_prompt_includes_skill_arg_schema(monkeypatch):
    captured = {}

    def fake_step(messages, tools, system="", tool_choice=None):
        captured["prompt"] = messages[0]["content"]
        return FakeResp("tool_use", [FakeBlock("tool_use", "submit_plan", {"tasks": [{"skill": "x", "goal": "y", "label": "z"}]})])

    monkeypatch.setattr(harness, "agent_step", fake_step)
    harness.plan("crawl xhs")

    assert "args_schema" in captured["prompt"]
    assert "--keyword" in captured["prompt"]


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


@pytest.mark.unit
def test_android_skills_registered():
    assert harness.SKILL_REGISTRY["android_explore"]["type"] == "android"
    assert harness.SKILL_REGISTRY["android_diagnostics"]["type"] == "android"
    assert "skill:showcase/android/xiaohongshu_note/xiaohongshu_note" in harness.SKILL_REGISTRY


@pytest.mark.unit
def test_ios_semi_auto_registered():
    assert harness.SKILL_REGISTRY["ios_semi_auto"]["type"] == "skill"
    assert harness.SKILL_REGISTRY["ios_semi_auto"]["path"] == "showcase/mobile/iphone_assist/iphone_assist"
    assert "skill:showcase/mobile/iphone_assist/iphone_assist" in harness.SKILL_REGISTRY


@pytest.mark.unit
def test_run_task_dispatches_android(monkeypatch):
    calls = []

    async def fake_run_android(goal, trace=None):
        calls.append(goal)
        if trace is not None:
            trace.append({"tool": "android_devices", "args": {}, "is_error": False})
        return {"status": "ok", "result": "android done"}

    class FakeLog:
        def step(self, msg):
            pass

    monkeypatch.setattr(harness, "run_android", fake_run_android)
    result = asyncio.run(harness._run_task({
        "skill": "android_explore",
        "goal": "打开手机并截图",
        "label": "手机探索",
    }, FakeLog()))

    assert result["status"] == "ok"
    assert result["skill"] == "android_explore"
    assert "android_devices" in calls[0]
    assert result["trace"][0]["tool"] == "android_devices"
    assert "屏幕比例坐标" in calls[0]


@pytest.mark.unit
def test_export_plan_includes_android_template(tmp_path):
    out = tmp_path / "android_flow.py"
    harness.export_plan("操作手机", [{
        "skill": "android_explore",
        "goal": "截图后点击中间",
        "label": "手机步骤",
    }], str(out))

    text = out.read_text(encoding="utf-8")
    assert "from core.android import AndroidDevice" in text
    assert "dev = AndroidDevice()" in text
    assert "tap_ratio" in text
    assert "待确认" in text


@pytest.mark.unit
def test_run_task_dispatches_saved_skill(monkeypatch):
    calls = []

    async def fake_run_saved_skill(spec, task):
        calls.append((spec, task))
        return {"status": "ok", "result": "skill done"}

    class FakeLog:
        def step(self, msg):
            pass

    monkeypatch.setattr(harness, "_run_saved_skill", fake_run_saved_skill)
    result = asyncio.run(harness._run_task({
        "skill": "skill:showcase/android/xiaohongshu_note/xiaohongshu_note",
        "goal": "生成小红书笔记草稿",
        "args": ["--dry-run", "--profile", "data/xhs_profile.json"],
        "label": "小红书草稿",
    }, FakeLog()))

    assert result["status"] == "ok"
    assert calls[0][0]["type"] == "skill"
    assert calls[0][1]["args"][0] == "--dry-run"


@pytest.mark.unit
def test_saved_skill_rejects_missing_required_arg():
    spec = harness.SKILL_REGISTRY["skill:showcase/web/xiaohongshu/search_posts"]

    result = asyncio.run(harness._run_saved_skill(spec, {"args": ["--limit", "1"]}))

    assert result["status"] == "error"
    assert "missing required arg" in result["error"]


@pytest.mark.unit
def test_external_commit_requires_confirmation(monkeypatch):
    class FakeLog:
        def step(self, msg):
            pass

    result = asyncio.run(harness._run_task({
        "skill": "skill:showcase/android/xiaohongshu_note/xiaohongshu_note",
        "goal": "真实发布小红书笔记",
        "args": ["--profile", "data/xhs_profile.json", "--confirm-post"],
        "label": "发布",
    }, FakeLog()))

    assert result["status"] == "error"
    assert "--confirm-external" in result["error"]


@pytest.mark.unit
def test_export_trace_writes_browser_and_android_steps(tmp_path):
    out = tmp_path / "trace_skill.py"
    harness.export_trace("测试导出", [
        {
            "status": "ok",
            "label": "browser",
            "trace": [
                {"tool": "browser_navigate", "args": {"url": "https://example.com"}, "is_error": False},
                {"tool": "browser_click", "args": {"selector": "#go"}, "is_error": False},
            ],
        },
        {
            "status": "ok",
            "label": "android",
            "trace": [
                {"tool": "android_tap", "args": {"rx": 0.5, "ry": 0.25}, "is_error": False},
                {"tool": "android_tap_element", "args": {"text": "发布", "exact": True}, "is_error": False},
                {"tool": "android_type", "args": {"text": "你好", "unicode": True}, "is_error": False},
            ],
        },
    ], str(out))

    text = out.read_text(encoding="utf-8")
    assert "open_page('https://example.com')" in text
    assert "await page.click('#go')" in text
    assert "dev.tap_ratio(0.5, 0.25)" in text
    assert "dev.tap_ui_node(text='发布'" in text
    assert "restore_ime=True" in text
