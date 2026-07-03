"""
[Showcase / Web / 通用]
Skill: Browser + LLM Vision 点击（决策树第三路线 showcase）

适用场景：
  CSS 选择器不稳定（class 是哈希值、频繁改版）时，
  截图发给 LLM 描述元素位置，再用坐标点击。

与纯 Browser 自动化的区别：
  - 纯 Browser（extract_table.py）：用 CSS/text selector，零 AI 成本，稳定
  - 本 Skill：用 LLM 视觉识别坐标，每步消耗 token，但不依赖任何 selector

前提：
  Chrome 以 --remote-debugging-port=9222 启动并已登录目标系统。

用法：
  # 打开页面，用视觉识别点击按钮，截图确认结果
  python run.py showcase/web/click_by_vision/click_by_vision -- \\
    --url "https://example.com/admin" \\
    --action "点击右上角的「导出数据」按钮"

  # 不打开新 URL，在当前浏览器页面操作
  python run.py showcase/web/click_by_vision/click_by_vision -- \\
    --action "点击表格第一行的「编辑」链接"

  # dry-run：只截图不点击，用于确认 LLM 能否识别目标
  python run.py showcase/web/click_by_vision/click_by_vision -- \\
    --url "https://example.com" --action "导出按钮" --dry-run
"""

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

from core.browser import open_page
from core.llm import find_element
from core.logger import SkillLogger


async def _run(args):
    log = SkillLogger("web/click_by_vision")

    async with open_page(args.url or None) as page:
        log.step(f"当前页面：{page.url}")

        # 截图发给 LLM，识别目标元素坐标
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        await page.screenshot(path=tmp.name)
        log.step("截图完成，发送给 LLM 识别")

        try:
            coords = find_element(args.action, tmp.name)
        except RuntimeError as e:
            Path(tmp.name).unlink(missing_ok=True)
            print(f"\n{e}")
            log.finish({"status": "error", "message": str(e)})
            return
        Path(tmp.name).unlink(missing_ok=True)

        if not coords:
            log.finish({"status": "error", "message": "LLM 未能识别目标元素"})
            print(f"未找到「{args.action}」，请检查描述是否足够具体，或页面是否已正确加载。")
            return

        x, y = coords["x"], coords["y"]
        log.step(f"LLM 识别到坐标：({x}, {y})")
        print(f"识别到「{args.action}」位于 ({x}, {y})")

        if args.dry_run:
            log.finish({"dry_run": True, "coords": coords})
            print("Dry-run 模式，不点击。")
            return

        # 用坐标点击（不依赖任何 selector）
        await page.mouse.click(x, y)
        log.step("点击完成，截图确认结果")

        # 等待可能的页面响应
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        result_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        await page.screenshot(path=result_tmp.name)
        result_path = result_tmp.name

        log.finish({"status": "ok", "coords": coords, "screenshot": result_path})
        print(f"点击完成，结果截图已保存：{result_path}")


# main 保持 async：run.py 会在事件循环内统一关闭 BrowserManager，
# 同步 main 自己 asyncio.run 的话 Playwright 清理不到（Windows 上退出报错）
async def main():
    parser = argparse.ArgumentParser(description="Browser + LLM Vision 点击")
    parser.add_argument("--url", default="", help="目标页面 URL（不填则用当前浏览器页面）")
    parser.add_argument("--action", required=True, help="要点击的元素描述，如「右上角的导出按钮」")
    parser.add_argument("--dry-run", action="store_true", help="只识别坐标，不实际点击")

    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1:]
    except ValueError:
        argv = sys.argv[1:]

    args = parser.parse_args(argv)
    await _run(args)


if __name__ == "__main__":
    asyncio.run(main())
