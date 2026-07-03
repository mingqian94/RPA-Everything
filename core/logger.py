"""
执行日志：记录每次 Skill 运行的时间、步骤、结果。
日志写入 logs/ 目录，便于审计和问题排查。
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from core import notify

_LOG_DIR = Path(__file__).parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

# 控制台输出
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rpa")


class SkillLogger:
    """记录单次 Skill 执行的结构化日志"""

    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.started_at = datetime.now()
        self.steps: list[dict] = []
        self._file = _LOG_DIR / f"{skill_name.replace('/', '_')}_{self.started_at.strftime('%Y%m%d_%H%M%S')}.json"

    def step(self, name: str, status: str = "ok", detail: str = ""):
        entry = {"step": name, "status": status, "detail": detail, "time": datetime.now().isoformat()}
        self.steps.append(entry)
        level = logging.INFO if status == "ok" else logging.WARNING
        logger.log(level, f"[{self.skill_name}] {name} → {status} {detail}")

    def finish(self, result=None):
        record = {
            "skill": self.skill_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": datetime.now().isoformat(),
            "steps": self.steps,
            "result": result,
        }
        self._file.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        logger.info(f"[{self.skill_name}] 完成，日志：{self._file}")

        # 如果 result 包含失败信息，自动发送通知
        self._maybe_notify(result)

        return record

    def _maybe_notify(self, result) -> None:
        """检测 result 中是否包含错误信息，有则触发通知。"""
        error_body: str | None = None

        if isinstance(result, dict):
            # result 字典中有 "error" key
            if "error" in result:
                error_body = str(result["error"])
        elif isinstance(result, str):
            # result 是字符串且包含失败关键词。用词边界匹配 error，
            # 避免 "0 errors"、"error-free" 这类正常文案触发误报。
            import re
            if re.search(r"\berror\b", result, re.IGNORECASE) or "失败" in result:
                error_body = result

        if error_body is not None:
            notify.send(
                title=f"Skill 失败：{self.skill_name}",
                body=error_body,
                level="error",
            )

    def error(self, msg: str) -> None:
        """记录错误日志，打印到 stderr 并发送通知。"""
        print(f"[{self.skill_name}] ERROR: {msg}", file=sys.stderr)
        notify.send(
            title=f"Skill 错误：{self.skill_name}",
            body=msg,
            level="error",
        )
