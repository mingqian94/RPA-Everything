"""
通知模块：在 Skill 运行失败时推送告警。

config.yaml 新增配置说明（不自动修改 config.yaml，请手动添加）：

  notify:
    webhook: ""   # 失败时推送到此 webhook，留空则不通知
                  # 兼容 Slack / 飞书机器人 Webhook URL

通知内容为 POST JSON：{"text": "[{level}] {title}\n{body}"}
超时 5s，失败静默，不抛异常。
"""

from __future__ import annotations

import sys

import requests

from core.config import get


def send(title: str, body: str, level: str = "error") -> None:
    """发送通知，失败时静默（不抛异常）。

    Args:
        title: 通知标题，通常为 skill 名称或错误类型。
        body:  通知正文，通常为错误详情或堆栈信息。
        level: 通知级别，默认 "error"，也可传 "warn"/"info"。
    """
    webhook: str | None = get("notify.webhook")
    if not webhook:
        return

    text = f"[{level}] {title}\n{body}"
    try:
        resp = requests.post(
            webhook,
            json={"text": text},
            timeout=5,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        # 通知失败不影响主流程，仅打印到 stderr
        print(f"[notify] 发送失败（静默）: {exc}", file=sys.stderr)
