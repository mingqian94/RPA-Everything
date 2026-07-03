"""
执行后结果验证（LLM-as-judge）。
SOP 文档作为验收标准，截图为证据，返回结构化判断。
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass


@dataclass
class VerifyResult:
    ok: bool
    reason: str
    screenshot: str = ""


class VerifyContext:
    def desktop_screenshot(self) -> str:
        """截取整个桌面，返回临时 PNG 文件路径。"""
        # 复用 core.desktop：macOS 优先 screencapture、错误提示带权限指引，
        # 且临时文件用 mkstemp（NamedTemporaryFile 的句柄不关，Windows 上写同一路径会报错）
        from .desktop import screenshot
        return screenshot()

    async def browser_screenshot(self, page) -> str:
        """截取当前 Playwright page，返回临时 PNG 文件路径。"""
        import os
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        await page.screenshot(path=path)
        return path

    def judge(self, sop: str, screenshot_path: str) -> VerifyResult:
        """截图 + SOP → LLM 判断任务是否已按规范完成。"""
        from .llm import judge as llm_judge
        question = (
            "根据以上操作规范，截图中的界面是否显示任务已按规范完成？\n"
            "重点对照规范中描述的最终状态，判断是否达到。"
        )
        data = llm_judge(
            question,
            screenshot_path,
            context=f"操作规范（SOP）：\n{sop}",
        )
        return VerifyResult(
            ok=bool(data.get("ok")),
            reason=data.get("reason", ""),
            screenshot=screenshot_path,
        )
