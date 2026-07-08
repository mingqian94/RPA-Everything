"""Standard output paths for Skill run artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.skills import ROOT

OUTPUT_ROOT = ROOT / "data" / "outputs"


def safe_name(name: str) -> str:
    return name.strip().replace("\\", "/").strip("/").replace("/", "_") or "skill"


def run_output_dir(skill_name: str, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_ROOT / safe_name(skill_name) / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_path(skill_name: str, filename: str = "result.json", when: datetime | None = None) -> Path:
    return run_output_dir(skill_name, when=when) / filename


def write_json_artifact(data, skill_name: str, output: str = "", filename: str = "result.json") -> Path:
    path = Path(output) if output else output_path(skill_name, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
