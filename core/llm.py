"""
Claude API 封装。
仅在需要判断、生成内容、或视觉兜底时调用，不用于常规流程。
"""

from __future__ import annotations

import base64
import os

import anthropic
from .config import get

# 惰性初始化：首次调用时才读配置、建 client，import 本模块无副作用
_client_instance: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client_instance
    if _client_instance is None:
        api_key = get("llm.api_key") or os.environ.get("ANTHROPIC_API_KEY")
        base_url = get("llm.base_url") or os.environ.get("ANTHROPIC_BASE_URL")
        kwargs = {"api_key": api_key, "timeout": 90.0}
        if base_url:
            kwargs["base_url"] = base_url
        _client_instance = anthropic.Anthropic(**kwargs)
    return _client_instance


def _model() -> str:
    return get("llm.model") or "claude-haiku-4-5-20251001"


def is_vision_unsupported(e: Exception) -> bool:
    """判断异常是否为「模型不支持图片输入」。
    只认 API 的 400 类错误且信息里提到 image/multimodal/vision，
    避免用 `"400" in str(e)` 这种子串匹配误伤其他错误。"""
    if not isinstance(e, anthropic.BadRequestError):
        return False
    msg = str(e).lower()
    return any(kw in msg for kw in ("image", "multimodal", "vision"))


def generate(prompt: str, context: str = "", max_tokens: int = 1024) -> str:
    """生成文本内容，用于消息文案、摘要等场景"""
    messages = [{"role": "user", "content": f"{context}\n\n{prompt}" if context else prompt}]
    resp = _get_client().messages.create(model=_model(), max_tokens=max_tokens, messages=messages)
    return resp.content[0].text


def generate_batch(prompt_template: str, items: list[dict]) -> list[str]:
    """为每条数据生成个性化内容，一次调用覆盖所有条目"""
    items_text = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    full_prompt = f"{prompt_template}\n\n数据列表：\n{items_text}\n\n请逐条输出，每条一行，格式：序号. 内容"
    result = generate(full_prompt)
    lines = [line.split(". ", 1)[-1].strip() for line in result.splitlines() if line.strip()]
    return lines


def generate_vision(prompt: str, screenshot_path: str, system: str = "", max_tokens: int = 2048) -> str:
    """带截图的内容生成（如根据页面截图生成代码）。需要多模态模型。"""
    with open(screenshot_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode()
    kwargs = dict(
        model=_model(), max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    if system:
        kwargs["system"] = system
    try:
        resp = _get_client().messages.create(**kwargs)
    except Exception as e:
        if is_vision_unsupported(e):
            raise RuntimeError(
                f"当前模型 {_model()!r} 不支持视觉输入，请在 config.yaml 中配置多模态模型（如 claude-sonnet-4-6）。"
            ) from e
        raise
    return resp.content[0].text.strip()


def decide(question: str, screenshot_path: str | None = None) -> str:
    """
    让 Claude 做判断，返回简短答案。
    screenshot_path: 传入截图路径时启用视觉理解。
    """
    content = []
    if screenshot_path:
        with open(screenshot_path, "rb") as f:
            img_data = base64.standard_b64encode(f.read()).decode()
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_data}})
    content.append({"type": "text", "text": question + "\n请用一句话回答。"})
    resp = _get_client().messages.create(model=_model(), max_tokens=256, messages=[{"role": "user", "content": content}])
    return resp.content[0].text.strip()


def agent_step(messages: list[dict], tools: list[dict], system: str = "", tool_choice: dict | None = None) -> object:
    """单步 agentic loop 调用，返回原始 Anthropic response 对象。
    供 harness/subagent.py 使用，调用方负责处理 tool_use 分支。
    tool_choice: 如 {"type": "tool", "name": "xxx"} 可强制模型调用指定工具（结构化输出）。
    """
    kwargs = dict(model=_model(), max_tokens=4096, tools=tools, messages=messages)
    if system:
        kwargs["system"] = system
    if tool_choice:
        kwargs["tool_choice"] = tool_choice
    return _get_client().messages.create(**kwargs)


def judge(question: str, screenshot_path: str, context: str = "") -> dict:
    """
    LLM-as-judge：截图 + 问题 → {"ok": bool, "reason": str}
    context 可传入 SOP 等背景文字，追加在问题前面。
    """
    import json as _json
    import re as _re
    with open(screenshot_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode()
    prompt = f"{context}\n\n{question}" if context else question
    prompt += '\n\n只返回 JSON：{"ok": true/false, "reason": "一句话说明"}'
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_data}},
        {"type": "text", "text": prompt},
    ]
    try:
        resp = _get_client().messages.create(
            model=_model(), max_tokens=256,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:
        if is_vision_unsupported(e):
            raise RuntimeError(
                f"当前模型 {_model()!r} 不支持视觉输入，verify 需要多模态模型（如 claude-sonnet-4-6）。\n"
                "请在 config.yaml 中配置 llm.model。"
            ) from e
        raise
    text = resp.content[0].text.strip()
    match = _re.search(r'\{.*?\}', text, _re.DOTALL)
    if match:
        try:
            return _json.loads(match.group())
        except Exception:
            pass
    return {"ok": False, "reason": f"LLM 返回格式异常：{text[:100]}"}


def find_element(description: str, screenshot_path: str) -> dict | None:
    """
    视觉定位兜底：截图 + 描述 → 返回坐标 {"x": int, "y": int}
    仅在 Playwright 选择器失败、且没有可用的图像模板时调用。
    需要多模态模型支持（如 claude-*、gpt-4o），纯文本模型会返回 None。
    """
    import json as _json
    import re as _re
    with open(screenshot_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode()
    prompt = (
        f"请找到截图中「{description}」的位置，"
        "以 JSON 格式返回坐标：{\"x\": 数字, \"y\": 数字}，坐标为像素值，不要其他内容。"
    )
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_data}},
        {"type": "text", "text": prompt},
    ]
    try:
        resp = _get_client().messages.create(model=_model(), max_tokens=64, messages=[{"role": "user", "content": content}])
    except Exception as e:
        if is_vision_unsupported(e):
            raise RuntimeError(
                f"当前模型 {_model()!r} 不支持视觉输入，无法使用 Browser+LLM Vision 路线。\n"
                "请在 config.yaml 中配置支持多模态的模型（如 claude-sonnet-4-6）。"
            ) from e
        raise
    match = _re.search(r'\{.*?\}', resp.content[0].text)
    if match:
        return _json.loads(match.group())
    return None
