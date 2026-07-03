"""
[Showcase / Desktop]
Skill: 图像模板匹配点击 —— 桌面自动化路线的最小可运行示例

演示 core.desktop.locate_and_click()：给一张目标元素的截图（模板），
在当前屏幕上定位并点击它的中心。零 AI 成本、确定性、抗小幅缩放漂移。

准备模板：
  1. 把目标按钮/图标截图存为 PNG（macOS: Cmd+Shift+4；Windows: Win+Shift+S）
  2. 按约定放到 assets/<系统名>/ 下，如 assets/feishu/approve_btn.png
  3. 截图范围贴着元素边缘，别带太多背景——背景变化会拉低匹配置信度

用法：
  python run.py showcase/app/template_click/template_click -- --template assets/feishu/approve_btn.png
  python run.py showcase/app/template_click/template_click -- --template x.png --app "飞书" --double
"""

import argparse
import sys

from core.desktop import activate_app, locate_and_click
from core.logger import SkillLogger


def main():
    parser = argparse.ArgumentParser(description="图像模板匹配点击")
    parser.add_argument("--template", required=True, help="模板图片路径（PNG）")
    parser.add_argument("--app", default="", help="先把该应用切到前台，如「飞书」")
    parser.add_argument("--double", action="store_true", help="双击")
    parser.add_argument("--confidence", type=float, default=0.85, help="匹配置信度，默认 0.85")
    parser.add_argument("--timeout", type=float, default=5.0, help="查找超时（秒），默认 5")

    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1:]
    except ValueError:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)

    log = SkillLogger("app/template_click")

    if args.app:
        activate_app(args.app)
        log.step(f"切换到前台：{args.app}")

    found = locate_and_click(
        args.template,
        confidence=args.confidence,
        double=args.double,
        timeout=args.timeout,
    )

    if found:
        log.step(f"已定位并点击：{args.template}")
        log.finish({"clicked": True, "template": args.template})
    else:
        log.step(f"未找到模板：{args.template}", status="fail")
        log.finish({"clicked": False, "error": f"超时 {args.timeout}s 未在屏幕上找到模板，"
                                               "检查模板是否为当前分辨率下截取、目标是否在前台"})
        sys.exit(1)


if __name__ == "__main__":
    main()
