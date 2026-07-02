"""
飞书 API 客户端。
文档：https://open.feishu.cn/document/home/index
"""

import time
import requests
from core.config import get

_APP_ID = get("feishu.app_id")
_APP_SECRET = get("feishu.app_secret")
_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
_MSG_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

_token_cache = {"token": None, "expires_at": 0}


def _get_token() -> str:
    if time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    resp = requests.post(_TOKEN_URL, json={"app_id": _APP_ID, "app_secret": _APP_SECRET}).json()
    _token_cache["token"] = resp["tenant_access_token"]
    _token_cache["expires_at"] = time.time() + resp["expire"]
    return _token_cache["token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


def send(open_id: str, content: str) -> bool:
    """发送文本消息给单个用户（open_id）"""
    resp = requests.post(
        _MSG_URL,
        headers=_headers(),
        params={"receive_id_type": "open_id"},
        json={"receive_id": open_id, "msg_type": "text", "content": f'{{"text":"{content}"}}'},
    ).json()
    return resp.get("code") == 0


def send_batch(messages: list[dict]) -> list[bool]:
    """批量发送，每条格式：{"open_id": "...", "content": "消息内容"}"""
    return [send(m["open_id"], m["content"]) for m in messages]
