"""
测试 feishu_project_daily 的纯逻辑层：字段解析和报告生成。
不依赖浏览器或 LLM，使用 fixture 数据。
"""
from datetime import date, datetime, timezone, timedelta
from skills.feishu_project_daily import _parse_item, _build_field_keys, _print_report

PROJ = "testproj"
DUE_ID = "abc123"
FIELDS = _build_field_keys(PROJ, DUE_ID)
CST = timezone(timedelta(hours=8))


def _make_raw(name="需求A", owners=None, status="进行中", due_ms=None):
    owners = owners or ["张三"]
    raw = {"uiDataMap": {
        FIELDS["name"]:   {"uiValue": {"nameWithComment": {"value": name}}},
        FIELDS["owner"]:  {"uiValue": {"user": {"value": [{"name_cn": o} for o in owners]}}},
        FIELDS["status"]: {"uiValue": {"workItemStatus": {"value": [{"label": status}]}}},
    }}
    if due_ms is not None:
        raw["uiDataMap"][FIELDS["due"]] = {"uiValue": {"date": {"value": due_ms}}}
    return raw


def _date_ms(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=CST).timestamp() * 1000)


# ── _parse_item ───────────────────────────────────────────────────────────────

def test_parse_basic_fields():
    item = _parse_item(_make_raw(), FIELDS)
    assert item["name"] == "需求A"
    assert item["owners"] == ["张三"]
    assert item["status"] == "进行中"
    assert item["due"] is None


def test_parse_multiple_owners():
    item = _parse_item(_make_raw(owners=["张三", "李四"]), FIELDS)
    assert item["owners"] == ["张三", "李四"]


def test_parse_due_date():
    d = date(2026, 6, 30)
    item = _parse_item(_make_raw(due_ms=_date_ms(d)), FIELDS)
    assert item["due"] == d


def test_parse_no_name_returns_none():
    assert _parse_item({"uiDataMap": {}}, FIELDS) is None


def test_parse_no_due_when_field_absent():
    fields_no_due = _build_field_keys(PROJ, "")
    item = _parse_item(_make_raw(), fields_no_due)
    assert item["due"] is None


def test_parse_empty_owners_defaults_to_unassigned():
    raw = _make_raw()
    raw["uiDataMap"][FIELDS["owner"]] = {"uiValue": {"user": {"value": []}}}
    item = _parse_item(raw, FIELDS)
    assert item["owners"] == ["未分配"]


# ── _print_report ─────────────────────────────────────────────────────────────

def test_print_report_today_due(capsys):
    today = date(2026, 6, 30)
    items = [{"name": "重要需求", "owners": ["张三"], "status": "进行中", "due": today}]
    _print_report(items, today)
    out = capsys.readouterr().out
    assert "重要需求" in out
    assert "今日到期" in out


def test_print_report_overdue(capsys):
    today = date(2026, 6, 30)
    items = [{"name": "逾期需求", "owners": ["李四"], "status": "进行中",
              "due": date(2026, 6, 25)}]
    _print_report(items, today)
    out = capsys.readouterr().out
    assert "逾期" in out
    assert "5 天" in out


def test_print_report_done_not_in_overdue(capsys):
    today = date(2026, 6, 30)
    items = [{"name": "已完成需求", "owners": ["王五"], "status": "已完成",
              "due": date(2026, 6, 1)}]
    _print_report(items, today)
    out = capsys.readouterr().out
    assert "已延期未完成（0 条）" in out
