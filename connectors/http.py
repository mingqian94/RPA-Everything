"""
通用 HTTP 连接器，供需要直接调接口的 Skill 使用。
"""

import requests
from core.config import get

_DEFAULT_TIMEOUT = int(get("http.timeout") or 30)


def get_json(url: str, params: dict = None, headers: dict = None) -> dict:
    resp = requests.get(url, params=params, headers=headers, timeout=_DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def post_json(url: str, data: dict = None, headers: dict = None) -> dict:
    resp = requests.post(url, json=data, headers=headers, timeout=_DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
