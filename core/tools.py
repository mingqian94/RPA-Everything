"""
RPA 工具集：供 subagent 调用的原语。

每个工具返回 Claude API tool_result content 格式的列表：
  [{"type": "text", "text": "..."}, ...]
  或含图片：
  [{"type": "image", "source": {...}}, {"type": "text", "text": "..."}]
"""

import base64
import tempfile
from pathlib import Path

# ── 工具 Schema（Claude API 格式）────────────────────────────────────────────

BROWSER_TOOLS = [
    {
        "name": "browser_screenshot",
        "description": "截取当前浏览器页面截图，返回图片。每次操作后调用以确认结果。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "browser_navigate",
        "description": "在浏览器中打开指定 URL。",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "browser_click",
        "description": "点击页面元素。优先用 text（文字内容），选择器不稳定时用 text。",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "按可见文字点击"},
                "selector": {"type": "string", "description": "CSS 选择器"},
            },
        },
    },
    {
        "name": "browser_type",
        "description": "清空输入框并输入文字。",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "输入框 CSS 选择器"},
                "text": {"type": "string"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "browser_extract_text",
        "description": "提取页面（或指定区域）的文本内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS 选择器，不填则提取全页"},
            },
        },
    },
    {
        "name": "browser_evaluate",
        "description": "在页面中执行 JavaScript 并返回结果。可用于注入代码、操作复杂组件。",
        "input_schema": {
            "type": "object",
            "properties": {"js": {"type": "string", "description": "JS 表达式或语句"}},
            "required": ["js"],
        },
    },
    {
        "name": "task_complete",
        "description": "目标完成时调用，传入结果摘要。这是结束 agentic loop 的唯一方式。",
        "input_schema": {
            "type": "object",
            "properties": {"result": {"type": "string", "description": "完成情况摘要"}},
            "required": ["result"],
        },
    },
]

DESKTOP_TOOLS = [
    {
        "name": "desktop_screenshot",
        "description": "截取当前整个屏幕截图，返回图片。用于查看桌面应用界面和确认操作结果。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "desktop_click",
        "description": "在屏幕指定坐标处点击鼠标。必须先截图确认坐标再点击。",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "double": {"type": "boolean", "description": "是否双击，默认 false"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "desktop_type",
        "description": "在当前焦点处输入文字（需先点击目标输入框）。",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "task_complete",
        "description": "目标完成时调用，传入结果摘要。",
        "input_schema": {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        },
    },
]


# ── 工具执行器 ────────────────────────────────────────────────────────────────

def _img_content(path: str) -> list[dict]:
    data = base64.standard_b64encode(Path(path).read_bytes()).decode()
    Path(path).unlink(missing_ok=True)
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
        {"type": "text", "text": "截图完成。"},
    ]


async def execute_browser_tool(name: str, args: dict, page) -> list[dict]:
    if name == "browser_screenshot":
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        await page.screenshot(path=tmp.name)
        return _img_content(tmp.name)

    if name == "browser_navigate":
        await page.goto(args["url"])
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        return [{"type": "text", "text": f"已导航到：{page.url}"}]

    if name == "browser_click":
        text = args.get("text")
        selector = args.get("selector")
        if text:
            await page.click(f"text={text}")
        elif selector:
            await page.click(selector)
        else:
            return [{"type": "text", "text": "错误：需要 text 或 selector"}]
        return [{"type": "text", "text": "点击完成。"}]

    if name == "browser_type":
        await page.fill(args["selector"], args["text"])
        return [{"type": "text", "text": "输入完成。"}]

    if name == "browser_extract_text":
        selector = args.get("selector")
        if selector:
            el = await page.query_selector(selector)
            text = (await el.inner_text()) if el else "(未找到元素)"
        else:
            text = await page.evaluate("document.body.innerText")
        return [{"type": "text", "text": text[:5000]}]

    if name == "browser_evaluate":
        result = await page.evaluate(args["js"])
        return [{"type": "text", "text": str(result)}]

    return [{"type": "text", "text": f"未知工具：{name}"}]


def execute_desktop_tool(name: str, args: dict) -> list[dict]:
    from core.desktop import screenshot, click, type_text, physical_to_logical

    if name == "desktop_screenshot":
        path = screenshot()
        return _img_content(path)

    if name == "desktop_click":
        x, y = args.get("x"), args.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f"desktop_click 的 x/y 必须是两个独立的数字，收到 x={x!r}, y={y!r}")
        # LLM 是从 desktop_screenshot 的图片里读坐标的，那张图是物理像素（Retina 上可能是逻辑像素的
        # 2 倍），而 click() 期望逻辑像素，这里做一次换算，否则 Retina 屏幕上点击位置会偏移。
        lx, ly = physical_to_logical(x, y)
        click(lx, ly)
        return [{"type": "text", "text": f"已点击 ({x}, {y})。"}]

    if name == "desktop_type":
        type_text(args["text"])
        return [{"type": "text", "text": "输入完成。"}]

    return [{"type": "text", "text": f"未知工具：{name}"}]
