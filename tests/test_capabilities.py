"""Capability catalog tests."""

from core.capabilities import build_skill_registry


def test_registry_includes_builtins_and_discovered_skills():
    registry = build_skill_registry()

    assert registry["android_explore"]["type"] == "android"
    key = "skill:showcase/android/xhs_note/xhs_note"
    assert key in registry
    assert registry[key]["type"] == "skill"
    assert registry[key]["path"] == "showcase/android/xhs_note/xhs_note"
    assert registry[key]["side_effect_level"] == "external_draft"

    crawler = "skill:showcase/web/xhs/post_detail"
    assert crawler in registry
    assert registry[crawler]["side_effect_level"] == "none"

    search = registry["skill:showcase/web/xhs/search_posts"]
    args = {name: item for item in search["args_schema"] for name in item["names"]}
    assert args["--keyword"]["required"] is True
    assert "--output" in args
