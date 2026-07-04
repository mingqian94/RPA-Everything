"""
[Skills / 飞书项目]
Skill: 今日节点 & 延期需求日报

每天运行，输出：
  1. 今日到期的需求（按负责人）
  2. 已延期未完成的需求（按逾期天数排序）
  3. 各负责人正在跟进的需求汇总

原理：打开视图页后拦截飞书内部 API 响应（mget_ui_async），解析需求数据，
不依赖 DOM 选择器，页面改版不影响数据获取。

配置（config.yaml）：
  feishu_project:
    view_url: "https://project.feishu.cn/your-project/storyView/Xxx"
    project_key: "625eb563..."    # 字段前缀，从 mget_ui_async 响应中获取
    due_field_id: "a817fb"        # 截止日期自定义字段 ID，没有可留空

如何获取 project_key / due_field_id：
  打开视图页 → DevTools → Network → 过滤 mget_ui_async
  响应 JSON 结构：data.work_item_detail_v2["1"][<item_id>].uiDataMap
  字段 key 格式为 <project_key>_story_name / <project_key>_story_field_<due_field_id>

用法：
  python run.py skills/feishu_project_daily
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta

from core import intercept
from core.browser import BrowserManager
from core.config import get
from core.logger import SkillLogger

CST = timezone(timedelta(hours=8))
DONE_STATUSES = {"已全量", "已完成", "已关闭", "已取消", "已上线", "关闭", "已放弃"}


def _today() -> date:
    return datetime.now(CST).date()


def _build_field_keys(project_key: str, due_field_id: str) -> dict:
    return {
        "name":   f"{project_key}_story_name",
        "owner":  f"{project_key}_story_owner",
        "status": f"{project_key}_story_work_item_status",
        "due":    f"{project_key}_story_field_{due_field_id}" if due_field_id else None,
    }


def _parse_item(raw: dict, fields: dict) -> dict | None:
    ui = raw.get("uiDataMap", {})

    name_block = ui.get(fields["name"], {}).get("uiValue", {})
    name = (name_block.get("nameWithComment", {}).get("value")
            or name_block.get("text", {}).get("value", ""))
    if not name:
        return None

    owners = [
        u.get("name_cn") or u.get("name", "")
        for u in ui.get(fields["owner"], {}).get("uiValue", {}).get("user", {}).get("value", [])
    ]

    statuses = (ui.get(fields["status"], {})
                  .get("uiValue", {})
                  .get("workItemStatus", {})
                  .get("value", []))
    status = statuses[0].get("label", "") if statuses else ""

    due = None
    if fields["due"]:
        due_ms = (ui.get(fields["due"], {})
                    .get("uiValue", {})
                    .get("date", {})
                    .get("value"))
        if due_ms:
            due = datetime.fromtimestamp(due_ms / 1000, tz=CST).date()

    return {"name": name, "owners": owners or ["未分配"], "status": status, "due": due}


async def _collect_items(page, view_url: str, project_key: str) -> list[dict]:
    # 通用拦截器（core.intercept）负责 hook fetch/XHR + 轮询稳定；
    # 本 Skill 只关心飞书特有的接口名和数据结构
    await intercept.install(page)

    try:
        await page.goto(view_url)
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        await page.wait_for_load_state("domcontentloaded")

    responses = await intercept.collect(page, "mget_ui_async", settle_polls=2)

    # 从 mget_ui_async 响应里取出 work_item 明细
    raw_items = []
    for r in responses:
        detail = (((r["json"] or {}).get("data", {})
                   .get("work_item_detail_v2", {}) or {}).get("1", {})) or {}
        raw_items.extend(detail.values())

    if not raw_items:
        print(
            "⚠️  未拦截到任何 mget_ui_async 响应。可能原因：\n"
            "   - 未登录飞书项目（在 RPA Chrome 里手动打开视图页确认）\n"
            "   - view_url 不是需求视图页\n"
            "   - 飞书前端改用了非 fetch 的请求方式（本 Skill 只 hook 了 fetch）",
            flush=True,
        )
    due_field_id = get("feishu_project.due_field_id", "")
    fields = _build_field_keys(project_key, due_field_id)

    collected = []
    for raw in raw_items:
        item = _parse_item(raw, fields)
        if item:
            collected.append(item)
    return collected


def _print_report(items: list[dict], today: date) -> None:
    today_due = [i for i in items if i["due"] == today]
    overdue = sorted(
        [i for i in items if i["due"] and i["due"] < today and i["status"] not in DONE_STATUSES],
        key=lambda x: x["due"],
    )

    by_owner: dict[str, list] = defaultdict(list)
    for item in items:
        if item["status"] not in DONE_STATUSES:
            for owner in item["owners"]:
                by_owner[owner].append(item)

    sep = "=" * 52
    print(f"\n{sep}")
    print(f"  飞书项目日报  {today}")
    print(sep)

    print(f"\n📅 今日到期（{len(today_due)} 条）")
    if today_due:
        for i in today_due:
            print(f"  [{i['status']}] {i['name']}")
            print(f"        负责人：{'、'.join(i['owners'])}")
    else:
        print("  无")

    print(f"\n⚠️  已延期未完成（{len(overdue)} 条）")
    if overdue:
        for i in overdue:
            days = (today - i["due"]).days
            print(f"  [{i['status']}] {i['name']}")
            print(f"        负责人：{'、'.join(i['owners'])}  |  截止 {i['due']}（逾期 {days} 天）")
    else:
        print("  无")

    print("\n👤 各负责人在跟需求")
    for owner, owner_items in sorted(by_owner.items(), key=lambda x: -len(x[1])):
        print(f"\n  {owner}（{len(owner_items)} 条）")
        for i in sorted(owner_items, key=lambda x: x["due"] or date.max):
            due_str = str(i["due"]) if i["due"] else "无截止"
            flag = " ⚠️" if i["due"] and i["due"] < today else ""
            print(f"    [{i['status']}] {i['name']}  —  {due_str}{flag}")

    print(f"\n{sep}\n")


async def main():
    view_url = get("feishu_project.view_url")
    project_key = get("feishu_project.project_key")

    if not view_url or not project_key:
        raise ValueError(
            "请在 config.yaml 中填写 feishu_project.view_url 和 feishu_project.project_key\n"
            "获取方式见 skills/feishu_project_daily.py 顶部注释"
        )

    log = SkillLogger("feishu/project_daily")
    today = _today()
    log.step(f"开始拉取飞书项目数据，日期：{today}")

    page = await BrowserManager.new_page()
    try:
        items = await _collect_items(page, view_url, project_key)
    finally:
        await page.close()
        await BrowserManager.close()

    log.step(f"共获取 {len(items)} 条需求")
    _print_report(items, today)

    today_due = [i for i in items if i["due"] == today]
    overdue = [i for i in items if i["due"] and i["due"] < today and i["status"] not in DONE_STATUSES]
    log.finish({"total": len(items), "today_due": len(today_due), "overdue": len(overdue)})


if __name__ == "__main__":
    asyncio.run(main())
