"""Capability catalog tests."""

from core.capabilities import build_skill_registry


def test_registry_includes_builtins_and_discovered_skills():
    registry = build_skill_registry()

    assert registry["android_explore"]["type"] == "android"
    key = "skill:showcase/mobile/android/xhs_note/xhs_note"
    assert key in registry
    assert registry[key]["type"] == "skill"
    assert registry[key]["path"] == "showcase/mobile/android/xhs_note/xhs_note"
    assert registry[key]["side_effect_level"] == "external_draft"

    crawler = "skill:showcase/web/xhs/post_detail"
    assert crawler in registry
    assert registry[crawler]["side_effect_level"] == "none"

    search = registry["skill:showcase/web/xhs/search_posts"]
    args = {name: item for item in search["args_schema"] for name in item["names"]}
    assert args["--keyword"]["required"] is True
    assert "--output" in args


def test_desktop_app_showcase_is_registered_under_fallback_route():
    registry = build_skill_registry()
    key = "skill:showcase/app/desktop/template_click/template_click"

    assert key in registry
    assert "桌面 UI Skill" in registry[key]["hint"]
