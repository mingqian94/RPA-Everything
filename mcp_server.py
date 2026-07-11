"""
RPA Framework MCP Server

将框架核心能力暴露为 MCP 工具，供 Claude Desktop 对话式调用。
用户无需写代码，通过自然语言对话即可驱动自动化流程。

Claude Desktop 配置（~/.claude/claude_desktop_config.json）：
{
  "mcpServers": {
    "rpa-everything": {
      "command": "python",
      "args": ["/absolute/path/to/rpa-everything/mcp_server.py"]
    }
  }
}

启动前提：Chrome 以 --remote-debugging-port=9222 启动，并已登录目标系统。

工具定义与 agentic loop 共享同一份 schema（core/tools.py），
本文件只补充 MCP 特有的工具（Skill 管理、Harness、视觉点击）。
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

from core.tools import (
    ANDROID_TOOLS,
    BROWSER_TOOLS,
    DESKTOP_TOOLS,
    IOS_TOOLS,
    execute_android_tool,
    execute_browser_tool,
    execute_desktop_tool,
    execute_ios_tool,
)

server = Server("rpa-everything")

# task_complete 是 agentic loop 的终止信号，对 MCP 客户端没有意义
_SHARED_BROWSER = [t for t in BROWSER_TOOLS if t["name"] != "task_complete"]
_SHARED_DESKTOP = [t for t in DESKTOP_TOOLS if t["name"] != "task_complete"]
_SHARED_ANDROID = [t for t in ANDROID_TOOLS if t["name"] != "task_complete"]
_SHARED_IOS = [t for t in IOS_TOOLS if t["name"] != "task_complete"]
_BROWSER_NAMES = {t["name"] for t in _SHARED_BROWSER}
_DESKTOP_NAMES = {t["name"] for t in _SHARED_DESKTOP}
_ANDROID_NAMES = {t["name"] for t in _SHARED_ANDROID}
_IOS_NAMES = {t["name"] for t in _SHARED_IOS}

# ── MCP 特有工具（Claude schema 格式，与 core/tools.py 保持一致的写法）──────────

_MCP_ONLY_TOOLS = [
    {
        "name": "desktop_find_click",
        "description": "用自然语言描述屏幕上的元素，AI 自动定位坐标并点击。比 desktop_click 更智能，无需手动确认坐标。",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "元素描述，如「红色的发送按钮」「左上角的搜索框」"},
            },
            "required": ["description"],
        },
    },
    {
        "name": "skill_list",
        "description": "列出所有可用的 Skill（包含 Showcase 官方和用户自建）。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "skill_run",
        "description": "运行一个已保存的 Skill。",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_path": {"type": "string", "description": "Skill 路径，如 showcase/office/excel_toolkit/excel_toolkit"},
            },
            "required": ["skill_path"],
        },
    },
    {
        "name": "skill_save",
        "description": "将生成的 Skill 代码保存到 skills/ 目录，供后续复用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill 名称，如 crm/export_students"},
                "code": {"type": "string", "description": "Python Skill 代码"},
            },
            "required": ["name", "code"],
        },
    },
    {
        "name": "orchestrate",
        "description": (
            "【Harness】接受一个高层目标，自动规划并执行一系列 RPA 技能。"
            "例如：「帮我做 3 道入门 OJ 题」「查假期余额然后在飞书发签到帖」。"
            "dry_run=true 时只返回规划，不实际执行。"
            "export 填路径时，执行后将流程骨架导出为可复用的 Skill 脚本。"
            "export_trace 填路径时，执行后将实际工具调用轨迹导出为初稿 Skill 脚本。"
            "trace_json 填路径时，执行后将实际工具调用轨迹导出为可 replay 的 JSON。"
            "sop 填 SOP 文档本地路径时，执行后自动截图并用 LLM 验证结果是否符合规范。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "高层目标，自然语言"},
                "dry_run": {"type": "boolean", "description": "只规划不执行，默认 false"},
                "export": {"type": "string", "description": "导出骨架脚本的路径，如 skills/my_workflow.py，留空则不导出"},
                "export_trace": {"type": "string", "description": "导出实际工具调用轨迹脚本的路径，如 skills/my_workflow.py"},
                "trace_json": {"type": "string", "description": "导出可 replay 的工具调用轨迹 JSON 路径，如 data/outputs/trace.json"},
                "sop": {"type": "string", "description": "SOP 文档本地路径（.md/.txt），执行后截图验证结果，留空则跳过"},
                "confirm_external": {"type": "boolean", "description": "允许执行可能产生真实外部副作用的发布/审批/发送类任务"},
            },
            "required": ["goal"],
        },
    },
    {
        "name": "skill_solidify",
        "description": "将 Harness 导出的 trace JSON 固化为可监督首跑的 Skill，并返回语法检查和风险 review 清单。不会执行生成的 Skill。",
        "input_schema": {
            "type": "object",
            "properties": {
                "trace": {"type": "string", "description": "harness/agent --trace-json 导出的 JSON 路径"},
                "output": {"type": "string", "description": "输出 Skill 路径，例如 skills/my_workflow.py"},
            },
            "required": ["trace", "output"],
        },
    },
    {
        "name": "run_list",
        "description": "查询最近的 Skill 运行记录；用于查看失败、待人工确认和最近成功的任务。",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "可选：按 Skill 名称过滤"},
                "limit": {"type": "integer", "description": "最多返回多少条，默认 20"},
                "show": {"type": "string", "description": "可选：传入上一轮返回的 id，读取该运行详情"},
            },
        },
    },
]

ALL_TOOLS = _SHARED_BROWSER + _SHARED_DESKTOP + _SHARED_ANDROID + _SHARED_IOS + _MCP_ONLY_TOOLS


def _to_mcp_tool(schema: dict) -> types.Tool:
    return types.Tool(
        name=schema["name"],
        description=schema["description"],
        inputSchema=schema["input_schema"],
    )


def _to_mcp_content(content: list[dict]) -> list[types.TextContent | types.ImageContent]:
    """core/tools.py 的 Claude content 格式 → MCP content 格式。"""
    out = []
    for block in content:
        if block.get("type") == "image":
            src = block["source"]
            out.append(types.ImageContent(type="image", data=src["data"], mimeType=src["media_type"]))
        else:
            out.append(types.TextContent(type="text", text=block.get("text", "")))
    return out


def _text(msg: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=msg)]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [_to_mcp_tool(t) for t in ALL_TOOLS]


# ── MCP 特有工具的 handler ────────────────────────────────────────────────────


async def _handle_desktop_find_click(arguments: dict):
    from core.desktop import screenshot, click, physical_to_logical
    from core.llm import find_element

    path = await asyncio.to_thread(screenshot)
    try:
        coords = await asyncio.to_thread(find_element, arguments["description"], path)
    finally:
        Path(path).unlink(missing_ok=True)
    if coords:
        # find_element 是对着 screenshot()（物理像素）判断坐标的，click() 期望逻辑像素
        lx, ly = physical_to_logical(coords["x"], coords["y"])
        await asyncio.to_thread(click, lx, ly)
        return _text(f"找到并点击：({coords['x']}, {coords['y']})")
    return _text("未找到元素，请用 desktop_screenshot 确认当前屏幕内容")


async def _handle_skill_list(arguments: dict):
    from core.skills import list_skills
    return _text("\n".join(list_skills()) or "暂无 Skill")


async def _handle_skill_run(arguments: dict):
    import subprocess

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "run.py", arguments["skill_path"]],
            capture_output=True, text=True, cwd=str(ROOT), timeout=300,
        )
    except subprocess.TimeoutExpired:
        return _text("Skill 运行超时（300 秒），已终止")
    return _text(result.stdout + result.stderr or "运行完成")


from core.skills import safe_skill_path  # noqa: E402  分发表和测试都引用这个名字


async def _handle_skill_save(arguments: dict):
    skill_path = safe_skill_path(arguments["name"])
    if skill_path is None:
        return _text(f"非法 Skill 名称：{arguments['name']}（不允许跳出 skills/ 目录）")
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(arguments["code"], encoding="utf-8")
    return _text(f"已保存：{skill_path}\n运行：python run.py skills/{arguments['name']}")


async def _handle_orchestrate(arguments: dict):
    import subprocess

    cmd = [sys.executable, "run.py", "harness/agent", "--", "--goal", arguments["goal"]]
    if arguments.get("dry_run"):
        cmd.append("--dry-run")
    if arguments.get("export"):
        cmd += ["--export", arguments["export"]]
    if arguments.get("export_trace"):
        cmd += ["--export-trace", arguments["export_trace"]]
    if arguments.get("trace_json"):
        cmd += ["--trace-json", arguments["trace_json"]]
    if arguments.get("sop"):
        cmd += ["--sop", arguments["sop"]]
    if arguments.get("confirm_external"):
        cmd.append("--confirm-external")
    try:
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=600,
        )
    except subprocess.TimeoutExpired:
        return _text("Harness 执行超时（600 秒），已终止")
    return _text((result.stdout + result.stderr).strip() or "执行完成")


async def _handle_skill_solidify(arguments: dict):
    from harness.solidify import solidify_trace

    result = await asyncio.to_thread(solidify_trace, arguments["trace"], arguments["output"])
    return _text(json.dumps(result, ensure_ascii=False, indent=2))


async def _handle_run_list(arguments: dict):
    from harness.runs import get_run, list_runs

    if arguments.get("show"):
        result = await asyncio.to_thread(get_run, arguments["show"])
    else:
        result = await asyncio.to_thread(
            list_runs,
            skill=arguments.get("skill", ""),
            limit=max(1, int(arguments.get("limit", 20))),
        )
    return _text(json.dumps(result, ensure_ascii=False, indent=2))


_HANDLERS = {
    "desktop_find_click": _handle_desktop_find_click,
    "skill_list": _handle_skill_list,
    "skill_run": _handle_skill_run,
    "skill_save": _handle_skill_save,
    "orchestrate": _handle_orchestrate,
    "skill_solidify": _handle_skill_solidify,
    "run_list": _handle_run_list,
}


# ── 统一分发 ──────────────────────────────────────────────────────────────────


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent]:
    try:
        if name in _BROWSER_NAMES:
            from core.browser import BrowserManager
            page = await BrowserManager.current_page()
            return _to_mcp_content(await execute_browser_tool(name, arguments, page))

        if name in _DESKTOP_NAMES:
            content = await asyncio.to_thread(execute_desktop_tool, name, arguments)
            return _to_mcp_content(content)

        if name in _ANDROID_NAMES:
            content = await asyncio.to_thread(execute_android_tool, name, arguments)
            return _to_mcp_content(content)

        if name in _IOS_NAMES:
            content = await asyncio.to_thread(execute_ios_tool, name, arguments)
            return _to_mcp_content(content)

        handler = _HANDLERS.get(name)
        if handler is None:
            return _text(f"未知工具：{name}")
        return await handler(arguments)
    except Exception as e:
        # 统一兜底：把异常转成对 LLM 友好的错误信息，而不是裸 traceback
        return _text(f"工具 {name} 执行出错：{type(e).__name__}: {e}")


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rpa-everything",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
