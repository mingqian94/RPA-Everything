import os
import yaml
from pathlib import Path

from core.secrets import expand_secret_references

_ROOT = Path(__file__).parent.parent
_CONFIG_FILE = _ROOT / "config.yaml"


def _load() -> dict:
    if not _CONFIG_FILE.exists():
        return {}
    with open(_CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# 惰性加载：首次 get() 时才读 config.yaml，import 本模块无文件 IO 副作用
config: dict | None = None


def get(key: str, default=None):
    """支持点分隔路径，如 get('systems.crm.url')。
    优先级：config.yaml → 环境变量（点换下划线大写，如 LLM_API_KEY）→ default。
    显式配置的假值（False/0/空串）原样返回，不会被 default 覆盖。"""
    global config
    if config is None:
        config = _load()
    val = config
    for k in key.split("."):
        if not isinstance(val, dict) or k not in val:
            val = None
            break
        val = val[k]
    if val is None:  # 未配置或 yaml 里留空
        env = os.environ.get(key.upper().replace(".", "_"))
        return env if env is not None else default
    return expand_secret_references(val)
