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


def _list_skills():
    result = []
    for base in ["showcase", "skills"]:
        for p in sorted(Path(base).rglob("*.py")):
            if p.name.startswith("_"):
                continue
            rel = p.with_suffix("")
            result.append(str(rel))
    return result


def main():
    if len(sys.argv) < 2:
        print("用法：python run.py <skill路径>\n")
        skills = _list_skills()
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

    skill_path = sys.argv[1].replace("/", ".").replace("\\", ".")
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
        asyncio.run(mod.main())
    else:
        mod.main()


if __name__ == "__main__":
    main()
