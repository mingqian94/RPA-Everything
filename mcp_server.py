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
"""

import asyncio
import base64
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

from core.config import get
from core.logger import logger

server = Server("rpa-everything")


# ── 浏览器工具 ────────────────────────────────────────────────────────

async def _get_page():
    """复用 BrowserManager 的常驻 CDP 连接，返回当前活动标签页。
    MCP server 是长驻进程，不必每次调用都新建/销毁 Playwright 实例。"""
    from core.browser import BrowserManager
    if BrowserManager._browser is None:
        await BrowserManager._connect()
    context = BrowserManager._browser.contexts[0]
    if not context.pages:
        return await context.new_page()
    return context.pages[0]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="browser_navigate",
            description="在浏览器中打开指定 URL",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "要打开的网页地址"}},
                "required": ["url"],
            },
        ),
        types.Tool(
            name="browser_screenshot",
            description="截取当前浏览器页面的截图，用于查看页面内容和元素位置",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="browser_click",
            description="点击页面中的元素，优先用文字或 CSS 选择器定位",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS 选择器，如 .btn-export"},
                    "text": {"type": "string", "description": "按文字内容点击，如「导出」"},
                },
            },
        ),
        types.Tool(
            name="browser_type",
            description="在输入框中输入文字",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "输入框的 CSS 选择器"},
                    "text": {"type": "string", "description": "要输入的文字"},
                },
                "required": ["selector", "text"],
            },
        ),
        types.Tool(
            name="browser_extract_text",
            description="提取页面中指定区域的文本内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS 选择器，不填则提取全页面"},
                },
            },
        ),
        types.Tool(
            name="browser_extract_table",
            description="提取页面中表格数据，返回 JSON 格式的行列数据",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "表格的 CSS 选择器，默认 table"},
                },
            },
        ),
        types.Tool(
            name="desktop_screenshot",
            description="截取当前整个屏幕的截图，用于查看桌面应用界面和元素位置",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="desktop_click",
            description="在屏幕指定坐标处点击鼠标，需先用 desktop_screenshot 确认坐标",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "横坐标（像素）"},
                    "y": {"type": "integer", "description": "纵坐标（像素）"},
                    "double": {"type": "boolean", "description": "是否双击，默认 false"},
                },
                "required": ["x", "y"],
            },
        ),
        types.Tool(
            name="desktop_type",
            description="在当前焦点处输入文字（需先点击目标输入框）",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要输入的文字"},
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="desktop_hotkey",
            description="发送键盘快捷键，如 Cmd+C、Cmd+Tab",
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "按键列表，如 ['command', 'c'] 或 ['ctrl', 'v']",
                    },
                },
                "required": ["keys"],
            },
        ),
        types.Tool(
            name="desktop_find_click",
            description="用自然语言描述屏幕上的元素，AI 自动定位坐标并点击。比 desktop_click 更智能，无需手动确认坐标",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "元素描述，如「红色的发送按钮」「左上角的搜索框」"},
                },
                "required": ["description"],
            },
        ),
        types.Tool(
            name="skill_list",
            description="列出所有可用的 Skill（包含 Showcase 官方和用户自建）",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="skill_run",
            description="运行一个已保存的 Skill",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_path": {"type": "string", "description": "Skill 路径，如 showcase/office/excel_toolkit/excel_toolkit"},
                },
                "required": ["skill_path"],
            },
        ),
        types.Tool(
            name="skill_save",
            description="将生成的 Skill 代码保存到 skills/ 目录，供后续复用",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill 名称，如 crm/export_students"},
                    "code": {"type": "string", "description": "Python Skill 代码"},
                },
                "required": ["name", "code"],
            },
        ),
        types.Tool(
            name="orchestrate",
            description=(
                "【Harness】接受一个高层目标，自动规划并执行一系列 RPA 技能。"
                "例如：「帮我做 3 道入门 OJ 题」「查假期余额然后在飞书发签到帖」。"
                "dry_run=true 时只返回规划，不实际执行。"
                "export 填路径时，执行后将流程骨架导出为可复用的 Skill 脚本。"
                "sop 填 SOP 文档本地路径时，执行后自动截图并用 LLM 验证结果是否符合规范。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "高层目标，自然语言"},
                    "dry_run": {"type": "boolean", "description": "只规划不执行，默认 false"},
                    "export": {"type": "string", "description": "导出骨架脚本的路径，如 skills/my_workflow.py，留空则不导出"},
                    "sop": {"type": "string", "description": "SOP 文档本地路径（.md/.txt），执行后截图验证结果，留空则跳过"},
                },
                "required": ["goal"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent]:

    # ── 浏览器工具 ────────────────────────────────────────────────────

    if name == "browser_navigate":
        page = await _get_page()
        await page.goto(arguments["url"])
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        title = await page.title()
        return [types.TextContent(type="text", text=f"已打开：{title}\n{page.url}")]

    if name == "browser_screenshot":
        page = await _get_page()
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        await page.screenshot(path=tmp.name)
        data = base64.standard_b64encode(Path(tmp.name).read_bytes()).decode()
        Path(tmp.name).unlink(missing_ok=True)
        return [types.ImageContent(type="image", data=data, mimeType="image/png")]

    if name == "browser_click":
        if not arguments.get("text") and not arguments.get("selector"):
            return [types.TextContent(type="text", text="参数错误：text 和 selector 至少填一个")]
        page = await _get_page()
        if arguments.get("text"):
            await page.click(f"text={arguments['text']}")
        else:
            await page.click(arguments["selector"])
        return [types.TextContent(type="text", text="已点击")]

    if name == "browser_type":
        page = await _get_page()
        await page.fill(arguments["selector"], arguments["text"])
        return [types.TextContent(type="text", text="已输入")]

    if name == "browser_extract_text":
        page = await _get_page()
        sel = arguments.get("selector")
        if sel:
            el = await page.query_selector(sel)
            text = await el.inner_text() if el else ""
        else:
            text = await page.inner_text("body")
        return [types.TextContent(type="text", text=text[:4000])]

    if name == "browser_extract_table":
        page = await _get_page()
        sel = arguments.get("selector", "table")
        # 选择器作为参数传入，避免拼进 JS 字符串（含引号的选择器会导致语法错误）
        rows = await page.evaluate("""(sel) => {
            const table = document.querySelector(sel);
            if (!table) return [];
            const rows = Array.from(table.querySelectorAll('tr'));
            return rows.map(r => Array.from(r.querySelectorAll('th,td')).map(c => c.innerText.trim()));
        }""", sel)
        if not rows:
            return [types.TextContent(type="text", text="未找到表格")]
        headers, *data = rows
        records = [dict(zip(headers, row)) for row in data]
        return [types.TextContent(type="text", text=json.dumps(records, ensure_ascii=False, indent=2))]

    # ── 桌面工具 ──────────────────────────────────────────────────────

    if name == "desktop_screenshot":
        from core.desktop import screenshot
        import base64
        path = screenshot()
        data = base64.standard_b64encode(Path(path).read_bytes()).decode()
        Path(path).unlink(missing_ok=True)
        return [types.ImageContent(type="image", data=data, mimeType="image/png")]

    if name == "desktop_click":
        from core.desktop import click, double_click, physical_to_logical
        x, y = int(arguments["x"]), int(arguments["y"])
        # x/y 是 Claude Desktop 从 desktop_screenshot 图片（物理像素）里读出的坐标，
        # click()/double_click() 期望逻辑像素，Retina 屏幕上需要换算，否则点击位置会偏移。
        lx, ly = physical_to_logical(x, y)
        if arguments.get("double"):
            double_click(lx, ly)
        else:
            click(lx, ly)
        return [types.TextContent(type="text", text=f"已点击 ({x}, {y})")]

    if name == "desktop_type":
        from core.desktop import type_text
        type_text(arguments["text"])
        return [types.TextContent(type="text", text="已输入")]

    if name == "desktop_hotkey":
        from core.desktop import hotkey
        keys = arguments["keys"]  # e.g. ["ctrl", "c"]
        hotkey(*keys)
        return [types.TextContent(type="text", text=f"已执行快捷键：{'+'.join(keys)}")]

    if name == "desktop_find_click":
        from core.desktop import screenshot, click, physical_to_logical
        from core.llm import find_element
        path = screenshot()
        coords = find_element(arguments["description"], path)
        Path(path).unlink(missing_ok=True)
        if coords:
            # find_element 是对着 screenshot()（物理像素）判断坐标的，同样需要换算。
            lx, ly = physical_to_logical(coords["x"], coords["y"])
            click(lx, ly)
            return [types.TextContent(type="text", text=f"找到并点击：({coords['x']}, {coords['y']})")]
        return [types.TextContent(type="text", text="未找到元素，请用 desktop_screenshot 确认当前屏幕内容")]

    # ── Skill 管理 ────────────────────────────────────────────────────

    if name == "skill_list":
        skills = []
        for base in ["showcase", "skills"]:
            for p in sorted(ROOT.rglob(f"{base}/**/*.py")):
                if not p.name.startswith("_"):
                    skills.append(str(p.relative_to(ROOT).with_suffix("")))
        return [types.TextContent(type="text", text="\n".join(skills) or "暂无 Skill")]

    if name == "skill_run":
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, "run.py", arguments["skill_path"]],
                capture_output=True, text=True, cwd=str(ROOT), timeout=300,
            )
        except subprocess.TimeoutExpired:
            return [types.TextContent(type="text", text="Skill 运行超时（300 秒），已终止")]
        output = result.stdout + result.stderr
        return [types.TextContent(type="text", text=output or "运行完成")]

    if name == "skill_save":
        skills_dir = (ROOT / "skills").resolve()
        skill_path = (skills_dir / f"{arguments['name']}.py").resolve()
        # name 由 LLM 生成，必须限制在 skills/ 内，防止路径穿越写到任意位置
        if not skill_path.is_relative_to(skills_dir):
            return [types.TextContent(type="text", text=f"非法 Skill 名称：{arguments['name']}（不允许跳出 skills/ 目录）")]
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(arguments["code"], encoding="utf-8")
        return [types.TextContent(type="text", text=f"已保存：{skill_path}\n运行：python run.py skills/{arguments['name']}")]

    # ── Harness ───────────────────────────────────────────────────────

    if name == "orchestrate":
        import subprocess
        goal = arguments["goal"]
        dry_run = arguments.get("dry_run", False)
        export = arguments.get("export", "")
        sop = arguments.get("sop", "")
        cmd = [sys.executable, "run.py", "harness/agent", "--", "--goal", goal]
        if dry_run:
            cmd.append("--dry-run")
        if export:
            cmd += ["--export", export]
        if sop:
            cmd += ["--sop", sop]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=600)
        except subprocess.TimeoutExpired:
            return [types.TextContent(type="text", text="Harness 执行超时（600 秒），已终止")]
        output = (result.stdout + result.stderr).strip()
        return [types.TextContent(type="text", text=output or "执行完成")]

    return [types.TextContent(type="text", text=f"未知工具：{name}")]


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rpa-everything",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
