import os
import yaml
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_CONFIG_FILE = _ROOT / "config.yaml"


def _load() -> dict:
    if not _CONFIG_FILE.exists():
        return {}
    with open(_CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


config = _load()


def get(key: str, default=None):
    """支持点分隔路径，如 get('systems.crm.url')"""
    keys = key.split(".")
    val = config
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return val or default or os.environ.get(key.upper().replace(".", "_"))
