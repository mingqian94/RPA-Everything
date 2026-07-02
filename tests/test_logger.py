import json
import pytest
from core.logger import SkillLogger

# 用任意方法的 __globals__ 拿到 core.logger 的模块全局命名空间
_logger_globals = SkillLogger.__init__.__globals__


@pytest.fixture()
def logger(tmp_path, monkeypatch):
    monkeypatch.setitem(_logger_globals, "_LOG_DIR", tmp_path)
    return SkillLogger("test/skill")


def test_step_recorded(logger):
    logger.step("打开页面")
    logger.step("点击按钮")
    assert len(logger.steps) == 2
    assert logger.steps[0]["step"] == "打开页面"
    assert logger.steps[0]["status"] == "ok"


def test_finish_returns_record(logger):
    logger.step("完成")
    record = logger.finish({"count": 3})
    assert record["skill"] == "test/skill"
    assert record["result"]["count"] == 3
    assert "started_at" in record
    assert "finished_at" in record


def test_finish_writes_json_file(tmp_path, monkeypatch):
    monkeypatch.setitem(_logger_globals, "_LOG_DIR", tmp_path)
    log = SkillLogger("my_skill")
    log.step("s1")
    log.finish()

    files = list(tmp_path.glob("my_skill_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["skill"] == "my_skill"
    assert len(data["steps"]) == 1


def test_error_status_preserved(logger):
    logger.step("登录", status="error", detail="超时")
    assert logger.steps[0]["status"] == "error"
    assert logger.steps[0]["detail"] == "超时"
