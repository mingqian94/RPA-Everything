"""
统一入口：python run.py <skill路径>
支持 showcase/ 和 skills/ 两个来源

示例：
  python run.py showcase/office/excel_toolkit/excel_toolkit
  python run.py skills/my_custom_skill
"""

import sys
import asyncio
import importlib
from pathlib import Path

# Windows 控制台默认 GBK 编码，打不出中文/emoji 混合输出
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    # 支持 `rpa` 入口从项目根目录运行：skill 按 cwd 相对路径解析
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if len(sys.argv) < 2:
        from core.skills import list_skills
        print("用法：python run.py <skill路径>\n")
        skills = list_skills()
        if skills:
            print("可用 Skill：")
            prev_base = None
            for s in skills:
                base = s.split("/")[0]
                if base != prev_base:
                    label = "📦 官方 Showcase" if base == "showcase" else "🔧 自建 Skill"
                    print(f"\n  {label}")
                    prev_base = base
                print(f"    {s}")
        sys.exit(0)

    skill_path = sys.argv[1].removesuffix(".py").strip("/\\").replace("/", ".").replace("\\", ".")
    # Framework commands are not Skills. Give their argparse parser only the
    # arguments after the module path so `python run.py harness/doctor --fix` works.
    if skill_path in {"harness.doctor", "harness.runtime", "harness.demo", "harness.supervise"}:
        from harness import demo, doctor, runtime, supervise

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        commands = {
            "harness.doctor": doctor,
            "harness.runtime": runtime,
            "harness.demo": demo,
            "harness.supervise": supervise,
        }
        commands[skill_path].main()
        return

    try:
        mod = importlib.import_module(skill_path)
        # 如果 import 到的是包（目录）而非模块，尝试 package.basename
        if not hasattr(mod, "main"):
            leaf = skill_path.rsplit(".", 1)[-1]
            mod = importlib.import_module(f"{skill_path}.{leaf}")
    except ModuleNotFoundError:
        print(f"找不到 Skill：{skill_path}")
        sys.exit(1)

    if not hasattr(mod, "main"):
        print(f"Skill {skill_path} 没有 main() 函数")
        sys.exit(1)

    if asyncio.iscoroutinefunction(mod.main):
        async def _runner():
            try:
                await mod.main()
            finally:
                # Skill 忘记关 Playwright 时兜底：必须在事件循环内 stop，
                # 否则 Windows 上循环关闭后子进程被 GC 会报 "Event loop is closed"
                if "core.browser" in sys.modules:
                    from core.browser import BrowserManager
                    await BrowserManager.close()

        asyncio.run(_runner())
    else:
        mod.main()


if __name__ == "__main__":
    main()
