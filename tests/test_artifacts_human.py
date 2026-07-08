from datetime import datetime

import pytest

from core import artifacts, human


@pytest.mark.unit
def test_output_path_uses_standard_skill_directory():
    when = datetime(2026, 7, 8, 12, 30, 0)

    path = artifacts.output_path("web/xiaohongshu/search_posts", when=when)

    assert path.as_posix().endswith("data/outputs/web_xiaohongshu_search_posts/20260708_123000/result.json")


@pytest.mark.unit
def test_write_json_artifact_creates_file(tmp_path):
    path = tmp_path / "out.json"

    written = artifacts.write_json_artifact({"ok": True}, "demo/skill", str(path))

    assert written == path
    assert '"ok": true' in path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_human_jitter_respects_minimum(monkeypatch):
    monkeypatch.setattr(human.random, "uniform", lambda a, b: -10)

    assert human.jitter(1.0, minimum=0.2) == 0.2
