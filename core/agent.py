"""
core.agent — RPA Agent 执行单元

提供 run_browser / run_desktop 两个 agentic loop 函数，
供 skill 或 harness 调用，以 LLM 推理方式完成浏览器/桌面任务。

示例：
    from core.agent import run_browser
    from core.browser import BrowserManager

    page = await BrowserManager.new_page()
    result = await run_browser("在iTalent查询假期余额", page)
    await page.close()
"""

import asyncio
from core.llm import agent_step
from core.tools import (
    ANDROID_TOOLS,
    BROWSER_TOOLS,
    DESKTOP_TOOLS,
    execute_android_tool,
    execute_browser_tool,
    execute_desktop_tool,
)

async def _pause_if_login_required(page) -> None:
    """导航后检测是否跳到了登录页，若是则暂停等用户手动登录。"""
    from core.browser import is_login_page
    try:
        needs_login = await is_login_page(page)
    except Exception:
        return
    if not needs_login:
        return
    url = page.url
    print(f"\n🔐 检测到登录页：{url}", flush=True)
    print("   请在 Chrome 中完成登录，然后按回车继续...", flush=True)
    try:
        input()
    except EOFError:
        print("   （非交互模式，自动继续）", flush=True)


SYSTEM_PROMPT = """你是一个 RPA 执行 Agent，通过工具操作浏览器或桌面来完成目标。

工作原则：
- 操作后截图确认结果，再决定下一步
- 遇到错误换另一种方式，不要重复同样的操作
- 完成后必须调用 task_complete 工具，传入结果摘要
- 简洁行事，不要输出不必要的说明"""

MAX_STEPS = 30


def _strip_images(messages: list[dict]) -> list[dict]:
    """把 tool_result 里的图片 content block 去掉，只保留文字。
    用于模型不支持多模态时的降级。
    """
    cleaned = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            cleaned.append(msg)
            continue
        new_content = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                inner = block.get("content", [])
                text_only = [c for c in inner if isinstance(c, dict) and c.get("type") == "text"]
                if not text_only:
                    text_only = [{"type": "text", "text": "(截图已省略，模型不支持图片输入)"}]
                new_content.append({**block, "content": text_only})
            else:
                new_content.append(block)
        cleaned.append({**msg, "content": new_content})
    return cleaned


async def _call(messages, tools):
    """调用 agent_step，若模型不支持图片则自动降级重试。"""
    from core.llm import is_vision_unsupported
    try:
        return await asyncio.to_thread(agent_step, messages, tools, SYSTEM_PROMPT)
    except Exception as e:
        if is_vision_unsupported(e):
            return await asyncio.to_thread(
                agent_step, _strip_images(messages), tools, SYSTEM_PROMPT
            )
        raise


async def run_browser(goal: str, page) -> dict:
    """
    以浏览器为工具运行 subagent。
    page: 已连接的 Playwright Page 对象（由 harness 负责创建和关闭）。
    """
    messages = [{"role": "user", "content": goal}]
    consecutive_screenshots = 0

    for step in range(MAX_STEPS):
        resp = await _call(messages, BROWSER_TOOLS)
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            text = next((b.text for b in resp.content if hasattr(b, "text")), "完成")
            return {"status": "ok", "result": text}

        if resp.stop_reason != "tool_use":
            return {"status": "error", "error": f"意外 stop_reason: {resp.stop_reason}"}

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "task_complete":
                return {"status": "ok", "result": block.input.get("result", "完成")}
            # 截图循环保护：连续截图超过 5 次说明 agent 陷入盲循环
            if block.name == "browser_screenshot":
                consecutive_screenshots += 1
                if consecutive_screenshots >= 5:
                    return {"status": "error",
                            "error": "Agent 陷入截图循环（可能是模型不支持视觉输入），请换用支持多模态的模型"}
            else:
                consecutive_screenshots = 0
            try:
                content = await execute_browser_tool(block.name, block.input, page)
                is_error = False
            except Exception as e:
                content = [{"type": "text", "text": f"工具调用出错：{e}"}]
                is_error = True

            if block.name == "browser_navigate" and not is_error:
                await _pause_if_login_required(page)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return {"status": "error", "error": f"超过最大步数 {MAX_STEPS}"}


async def run_desktop(goal: str) -> dict:
    """
    以桌面为工具运行 subagent。
    不需要 page，直接操作屏幕。
    """
    messages = [{"role": "user", "content": goal}]

    for step in range(MAX_STEPS):
        resp = await _call(messages, DESKTOP_TOOLS)
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            text = next((b.text for b in resp.content if hasattr(b, "text")), "完成")
            return {"status": "ok", "result": text}

        if resp.stop_reason != "tool_use":
            return {"status": "error", "error": f"意外 stop_reason: {resp.stop_reason}"}

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "task_complete":
                return {"status": "ok", "result": block.input.get("result", "完成")}
            try:
                content = await asyncio.to_thread(execute_desktop_tool, block.name, block.input)
                is_error = False
            except Exception as e:
                content = [{"type": "text", "text": f"工具调用出错：{e}"}]
                is_error = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return {"status": "error", "error": f"超过最大步数 {MAX_STEPS}"}
async def run_android(goal: str) -> dict:
    """Run a subagent with Android/ADB tools."""
    messages = [{"role": "user", "content": goal}]
    consecutive_screenshots = 0

    for step in range(MAX_STEPS):
        resp = await _call(messages, ANDROID_TOOLS)
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            text = next((b.text for b in resp.content if hasattr(b, "text")), "done")
            return {"status": "ok", "result": text}

        if resp.stop_reason != "tool_use":
            return {"status": "error", "error": f"Unexpected stop_reason: {resp.stop_reason}"}

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "task_complete":
                return {"status": "ok", "result": block.input.get("result", "done")}
            if block.name == "android_screenshot":
                consecutive_screenshots += 1
                if consecutive_screenshots >= 5:
                    return {"status": "error", "error": "Agent is stuck taking Android screenshots repeatedly."}
            else:
                consecutive_screenshots = 0
            try:
                content = await asyncio.to_thread(execute_android_tool, block.name, block.input)
                is_error = False
            except Exception as e:
                content = [{"type": "text", "text": f"Tool call failed: {e}"}]
                is_error = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return {"status": "error", "error": f"Exceeded max steps: {MAX_STEPS}"}
