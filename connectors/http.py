"""
通用 HTTP 连接器，供需要直接调接口的 Skill 使用。
GET 对 502/503/504 自动重试 2 次（幂等）；POST 不重试。
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import get

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            # 默认 allowed_methods 只含幂等方法，POST 不会被重试
        )
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
    return _session


def _timeout() -> int:
    return int(get("http.timeout") or 30)


def get_json(url: str, params: dict = None, headers: dict = None) -> dict:
    resp = _get_session().get(url, params=params, headers=headers, timeout=_timeout())
    resp.raise_for_status()
    return resp.json()


def post_json(url: str, data: dict = None, headers: dict = None) -> dict:
    resp = _get_session().post(url, json=data, headers=headers, timeout=_timeout())
    resp.raise_for_status()
    return resp.json()
