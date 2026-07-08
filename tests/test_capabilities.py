"""Capability catalog tests."""

from core.capabilities import build_skill_registry


def test_registry_includes_builtins_and_discovered_skills():
    registry = build_skill_registry()

    assert registry["android_explore"]["type"] == "android"
    key = "skill:showcase/android/xiaohongshu_note/xiaohongshu_note"
    assert key in registry
    assert registry[key]["type"] == "skill"
    assert registry[key]["path"] == "showcase/android/xiaohongshu_note/xiaohongshu_note"
