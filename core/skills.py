"""
Skill 发现与保存的公共逻辑。
run.py / mcp_server.py / tools/generate_skill.py 共用，避免各写一份产生漂移。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


def list_skills() -> list[str]:
    """列出所有可运行的 Skill（showcase/ 官方示例 + skills/ 自建），
    返回相对项目根目录、正斜杠分隔、去掉 .py 后缀的路径。"""
    result = []
    for base in ["showcase", "skills"]:
        base_dir = ROOT / base
        if not base_dir.is_dir():
            continue
        for p in sorted(base_dir.rglob("*.py")):
            if p.name.startswith("_"):
                continue
            result.append(p.relative_to(ROOT).with_suffix("").as_posix())
    return result


def safe_skill_path(name: str) -> Path | None:
    """把（可能由 LLM 生成的）Skill 名称解析为 skills/ 内的安全路径。
    跳出 skills/ 目录（路径穿越）时返回 None。"""
    skills_dir = (ROOT / "skills").resolve()
    path = (skills_dir / f"{name}.py").resolve()
    if not path.is_relative_to(skills_dir):
        return None
    return path
