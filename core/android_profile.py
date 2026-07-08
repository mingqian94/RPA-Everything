"""Reusable Android device profile storage and validation.

Profiles keep device-specific coordinates as ratios, so generated Skills can
survive different screen resolutions better than fixed pixels.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.skills import ROOT


PROFILE_STORE = ROOT / "data" / "android_profiles.json"


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize an Android profile dictionary."""
    normalized = dict(profile)
    coords = normalized.get("coords", {})
    if not isinstance(coords, dict):
        raise ValueError("profile.coords must be an object.")

    for name, point in coords.items():
        if not isinstance(point, dict):
            raise ValueError(f"profile.coords.{name} must be an object.")
        if "rx" not in point or "ry" not in point:
            raise ValueError(f"profile.coords.{name} must include rx and ry.")
        rx, ry = float(point["rx"]), float(point["ry"])
        if not (0 <= rx <= 1 and 0 <= ry <= 1):
            raise ValueError(f"profile.coords.{name} rx/ry must be between 0 and 1.")
        point["rx"], point["ry"] = rx, ry

    normalized["coords"] = coords
    return normalized


def load_profiles(path: str | Path = PROFILE_STORE) -> dict[str, dict[str, Any]]:
    store = Path(path)
    if not store.exists():
        return {}
    data = json.loads(store.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Android profile store must be a JSON object.")
    return {str(k): validate_profile(v) for k, v in data.items()}


def save_profile(model: str, profile: dict[str, Any], path: str | Path = PROFILE_STORE) -> None:
    store = Path(path)
    store.parent.mkdir(parents=True, exist_ok=True)
    profiles = load_profiles(store)
    profiles[model] = validate_profile(profile)
    store.write_text(json.dumps(profiles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_profile(model: str, path: str | Path = PROFILE_STORE) -> dict[str, Any] | None:
    return load_profiles(path).get(model)


def profile_for_device(device, path: str | Path = PROFILE_STORE) -> dict[str, Any] | None:
    """Return the stored profile for an AndroidDevice-like object."""
    model = device.shell("getprop ro.product.model").strip()
    return get_profile(model, path)
