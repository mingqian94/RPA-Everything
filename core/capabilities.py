"""Capability catalog for the Harness planner.

The Harness should plan against what the repository can actually do.  This
module combines built-in agent capabilities with discovered runnable Skills
from ``showcase/`` and ``skills/``.
"""

from __future__ import annotations

import ast
from pathlib import Path

from core.skills import ROOT, list_skills


BUILTIN_CAPABILITIES: dict[str, dict] = {
    "extract_table": {
        "type": "browser",
        "side_effect_level": "none",
        "description": "从网页 HTML 表格提取数据并返回",
        "hint": "目标 URL 在 goal 中指定；用 browser_evaluate 提取 table 内容",
    },
    "browser_explore": {
        "type": "browser",
        "side_effect_level": "unknown",
        "description": "探索一个网页或浏览器系统，完成点击、输入、截图、文本/表格提取等通用浏览器任务",
        "hint": (
            "优先使用 DOM/CSS/文本定位；每个关键操作后截图或提取文本确认结果；"
            "如果目标是沉淀 Skill，记录稳定 selector 和必要前置登录状态"
        ),
    },
    "desktop_explore": {
        "type": "desktop",
        "side_effect_level": "unknown",
        "description": "探索本机桌面应用，完成截图、点击、输入、快捷键等通用桌面任务",
        "hint": (
            "先截图确认当前窗口和目标元素；中文输入走剪贴板；关键结果要截图确认。"
            "如果是长期复用流程，优先沉淀成模板匹配或确定性窗口操作，不要依赖一次性坐标"
        ),
    },
    "android_explore": {
        "type": "android",
        "side_effect_level": "unknown",
        "description": "探索已连接 Android 手机，完成设备发现、截图、点击、滑动、按键、输入和文件推送",
        "hint": (
            "先调用 android_devices / android_diagnostics 确认设备在线；"
            "优先使用 android_dump_ui / android_tap_element 按 text/resource-id/content-desc 操作；"
            "UIAutomator 找不到时再使用 0~1 屏幕比例坐标，避免写死像素；"
            "中文、emoji、换行文本用 android_type unicode=true；"
            "真实外部副作用（发布/发送/付款等）完成后只标记待确认，除非有明确成功信号"
        ),
    },
    "android_diagnostics": {
        "type": "android",
        "side_effect_level": "local",
        "description": "检查 Android 自动化前置条件：ADB 连接、截图、可选输入注入、文件推送等",
        "hint": (
            "先列出设备，再运行 android_diagnostics；"
            "默认不要启用输入检查，除非用户明确允许，因为 include_input_check 会发送 HOME"
        ),
    },
    "feishu_post": {
        "type": "desktop",
        "side_effect_level": "external_commit",
        "description": "向飞书圈子发帖",
        "hint": "飞书已在桌面端运行；先截图找到导航图标，点击进入圈子，找到发帖框填入内容，选择版块后点击发布",
    },
    "feishu_approve": {
        "type": "desktop",
        "side_effect_level": "external_commit",
        "description": "在飞书 App 中批量处理待审批单（如报表申请），逐一打开并点同意",
        "hint": (
            "飞书已在桌面端运行；点击左侧导航栏「审批」图标（或从消息通知进入）进入「待我审批」列表\n"
            "找到目标类型的审批单，点击进入详情，阅读申请内容后点击「同意」按钮\n"
            "如弹出确认框，点击确认；返回列表，重复直到没有该类型的待审批单\n"
            "审批单类型名称由 goal 中指定，需精确匹配"
        ),
    },
}


def _first_heading(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
            if stripped:
                return stripped[:120]
    except OSError:
        return ""
    return ""


def _read_skill_description(skill_path: str) -> str:
    path = ROOT / f"{skill_path}.py"
    readme = path.parent / "README.md"
    heading = _first_heading(readme)
    if heading:
        return f"运行已固化 Skill：{heading}"
    return f"运行已固化 Skill：{skill_path}"


def _literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def _argparse_schema(skill_path: str) -> list[dict]:
    path = ROOT / f"{skill_path}.py"
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    schema = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        names = [_literal(arg) for arg in node.args if isinstance(_literal(arg), str)]
        option_names = [n for n in names if n.startswith("-")]
        if not option_names:
            continue
        item = {
            "names": option_names,
            "dest": option_names[-1].lstrip("-").replace("-", "_"),
            "required": False,
            "action": "",
            "default": None,
            "help": "",
        }
        for kw in node.keywords:
            value = _literal(kw.value)
            if kw.arg == "required":
                item["required"] = bool(value)
            elif kw.arg == "action":
                item["action"] = value or ""
            elif kw.arg == "default":
                item["default"] = value
            elif kw.arg == "help":
                item["help"] = value or ""
            elif kw.arg == "nargs":
                item["nargs"] = value
            elif kw.arg == "type":
                if isinstance(kw.value, ast.Name):
                    item["type"] = kw.value.id
        schema.append(item)
    return schema


def _infer_side_effect_level(skill_path: str) -> str:
    lowered = skill_path.lower()
    if "xiaohongshu_note" in lowered:
        return "external_draft"
    if any(word in lowered for word in ["extract", "crawler", "crawl", "search", "detail", "user_posts", "post_detail"]):
        return "none"
    if any(word in lowered for word in ["post", "approve", "send", "publish"]):
        return "external_commit"
    return "unknown"


def build_skill_registry(include_discovered: bool = True) -> dict[str, dict]:
    """Return the capability registry used by the Harness planner."""
    registry = {k: dict(v) for k, v in BUILTIN_CAPABILITIES.items()}
    if not include_discovered:
        return registry

    for skill_path in list_skills():
        key = f"skill:{skill_path}"
        registry[key] = {
            "type": "skill",
            "side_effect_level": _infer_side_effect_level(skill_path),
            "description": _read_skill_description(skill_path),
            "args_schema": _argparse_schema(skill_path),
            "hint": (
                f"这是可直接运行的已固化 Skill：python run.py {skill_path}。"
                "如果需要参数，请在计划的 args 数组中给出 run.py -- 后面的 CLI 参数。"
            ),
            "path": skill_path,
        }
    return registry
