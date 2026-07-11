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
        "name": "browser_extract_table",
        "description": "提取页面中表格数据，返回 JSON 格式的行列数据。",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "表格的 CSS 选择器，默认 table"},
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
        "name": "desktop_hotkey",
        "description": "发送键盘快捷键，如 ['command', 'v']、['ctrl', 'c']。",
        "input_schema": {
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

ANDROID_TOOLS = [
    {
        "name": "android_devices",
        "description": "List online Android devices visible to adb.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "android_screenshot",
        "description": "Capture a screenshot from an Android device and return it as an image.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string", "description": "ADB device serial. Defaults to the first online device."},
            },
        },
    },
    {
        "name": "android_tap",
        "description": "Tap an Android device by absolute pixels (x/y) or screen ratio (rx/ry).",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "rx": {"type": "number", "description": "X ratio from 0 to 1."},
                "ry": {"type": "number", "description": "Y ratio from 0 to 1."},
            },
        },
    },
    {
        "name": "android_dump_ui",
        "description": "Dump Android UIAutomator nodes as JSON. Prefer this before screenshot-only coordinate guessing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
            },
        },
    },
    {
        "name": "android_tap_element",
        "description": "Tap an Android UI element by text, resource_id, or content_desc from UIAutomator.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "text": {"type": "string"},
                "resource_id": {"type": "string"},
                "content_desc": {"type": "string"},
                "exact": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "android_swipe",
        "description": "Swipe on an Android device by absolute pixels or screen ratios.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "x1": {"type": "integer"},
                "y1": {"type": "integer"},
                "x2": {"type": "integer"},
                "y2": {"type": "integer"},
                "rx1": {"type": "number"},
                "ry1": {"type": "number"},
                "rx2": {"type": "number"},
                "ry2": {"type": "number"},
                "duration_ms": {"type": "integer", "default": 300},
            },
        },
    },
    {
        "name": "android_key",
        "description": "Send an Android keyevent, such as KEYCODE_HOME, KEYCODE_BACK, or 4.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "keycode": {"type": "string"},
            },
            "required": ["keycode"],
        },
    },
    {
        "name": "android_type",
        "description": "Type text on Android. unicode=true uses ADBKeyboard's ADB_INPUT_B64 broadcast.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "text": {"type": "string"},
                "unicode": {"type": "boolean", "default": False},
                "restore_ime": {"type": "boolean", "default": True},
                "restore_ime_preferred": {"type": "string", "description": "Optional preferred IME to restore after ADBKeyboard input."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "android_push_file",
        "description": "Push a local file to the Android device, optionally triggering a media scan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "local_path": {"type": "string"},
                "remote_path": {"type": "string"},
                "media_scan": {"type": "boolean", "default": False},
            },
            "required": ["local_path", "remote_path"],
        },
    },
    {
        "name": "android_diagnostics",
        "description": "Run Android automation diagnostics. Input check is opt-in because it sends HOME.",
        "input_schema": {
            "type": "object",
            "properties": {
                "serial": {"type": "string"},
                "include_input_check": {"type": "boolean", "default": False},
                "include_file_check": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "task_complete",
        "description": "Call this when the Android task is complete.",
        "input_schema": {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        },
    },
]


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

    if name == "browser_extract_table":
        import json as _json
        sel = args.get("selector") or "table"
        # 选择器作为参数传入，避免拼进 JS 字符串（含引号的选择器会导致语法错误）
        rows = await page.evaluate("""(sel) => {
            const table = document.querySelector(sel);
            if (!table) return [];
            const rows = Array.from(table.querySelectorAll('tr'));
            return rows.map(r => Array.from(r.querySelectorAll('th,td')).map(c => c.innerText.trim()));
        }""", sel)
        if not rows:
            return [{"type": "text", "text": "未找到表格"}]
        headers, *data = rows
        records = [dict(zip(headers, row)) for row in data]
        return [{"type": "text", "text": _json.dumps(records, ensure_ascii=False, indent=2)}]

    if name == "browser_evaluate":
        result = await page.evaluate(args["js"])
        return [{"type": "text", "text": str(result)}]

    return [{"type": "text", "text": f"未知工具：{name}"}]


def execute_android_tool(name: str, args: dict) -> list[dict]:
    import json as _json
    import tempfile as _tempfile
    from core.android import AndroidDevice, list_devices, run_diagnostics

    if name == "android_devices":
        devices = [d.__dict__ for d in list_devices()]
        return [{"type": "text", "text": _json.dumps(devices, ensure_ascii=False, indent=2)}]

    if name == "android_screenshot":
        dev = AndroidDevice(serial=args.get("serial"))
        tmp = _tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        dev.screencap_to(tmp.name)
        return _img_content(tmp.name)

    if name == "android_tap":
        dev = AndroidDevice(serial=args.get("serial"))
        if "rx" in args and "ry" in args:
            dev.tap_ratio(float(args["rx"]), float(args["ry"]))
        elif "x" in args and "y" in args:
            dev.tap(int(args["x"]), int(args["y"]))
        else:
            return [{"type": "text", "text": "Error: provide x/y or rx/ry."}]
        return [{"type": "text", "text": "Android tap complete."}]

    if name == "android_dump_ui":
        dev = AndroidDevice(serial=args.get("serial"))
        nodes = [n.__dict__ for n in dev.ui_nodes()]
        return [{"type": "text", "text": _json.dumps(nodes, ensure_ascii=False, indent=2)[:12000]}]

    if name == "android_tap_element":
        dev = AndroidDevice(serial=args.get("serial"))
        node = dev.tap_ui_node(
            text=args.get("text", ""),
            resource_id=args.get("resource_id", ""),
            content_desc=args.get("content_desc", ""),
            exact=bool(args.get("exact", False)),
        )
        return [{"type": "text", "text": f"Android element tapped: {node.__dict__}"}]

    if name == "android_swipe":
        dev = AndroidDevice(serial=args.get("serial"))
        duration = int(args.get("duration_ms", 300))
        if all(k in args for k in ("rx1", "ry1", "rx2", "ry2")):
            dev.swipe_ratio(float(args["rx1"]), float(args["ry1"]), float(args["rx2"]), float(args["ry2"]), duration)
        elif all(k in args for k in ("x1", "y1", "x2", "y2")):
            dev.swipe(int(args["x1"]), int(args["y1"]), int(args["x2"]), int(args["y2"]), duration)
        else:
            return [{"type": "text", "text": "Error: provide x1/y1/x2/y2 or rx1/ry1/rx2/ry2."}]
        return [{"type": "text", "text": "Android swipe complete."}]

    if name == "android_key":
        dev = AndroidDevice(serial=args.get("serial"))
        dev.key(args["keycode"])
        return [{"type": "text", "text": f"Android key sent: {args['keycode']}"}]

    if name == "android_type":
        dev = AndroidDevice(serial=args.get("serial"))
        dev.input_text(
            args["text"],
            unicode=bool(args.get("unicode", False)),
            restore_ime=bool(args.get("restore_ime", True)),
            restore_ime_preferred=args.get("restore_ime_preferred", ""),
        )
        return [{"type": "text", "text": "Android text input complete."}]

    if name == "android_push_file":
        dev = AndroidDevice(serial=args.get("serial"))
        dev.push(args["local_path"], args["remote_path"])
        if args.get("media_scan"):
            dev.media_scan(args["remote_path"])
        return [{"type": "text", "text": f"Pushed to Android: {args['remote_path']}"}]

    if name == "android_diagnostics":
        results = [r.__dict__ for r in run_diagnostics(
            serial=args.get("serial"),
            include_input_check=bool(args.get("include_input_check", False)),
            include_file_check=bool(args.get("include_file_check", False)),
        )]
        return [{"type": "text", "text": _json.dumps(results, ensure_ascii=False, indent=2)}]

    return [{"type": "text", "text": f"Unknown Android tool: {name}"}]


def execute_desktop_tool(name: str, args: dict) -> list[dict]:
    from core.desktop import screenshot, click, type_text, hotkey, physical_to_logical

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

    if name == "desktop_hotkey":
        keys = args["keys"]
        hotkey(*keys)
        return [{"type": "text", "text": f"已执行快捷键：{'+'.join(keys)}"}]

    return [{"type": "text", "text": f"未知工具：{name}"}]
