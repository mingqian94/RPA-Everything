"""
[Harness]
RPA Harness Agent

定位：探索工具，不是生产执行器。
用 LLM 快速验证"这件事能自动化吗、需要哪几步"，搞清楚后固化成普通 Skill 定时跑。

固化路径：
  1. --dry-run 看规划是否合理
  2. --sop sop.md 提供操作规范，执行后自动截图验证结果
  3. 正式执行，确认每步能跑通
  4. --export skills/my_workflow.py  生成骨架脚本
  5. 把骨架里的 TODO 替换成确定性 Playwright 代码
  6. python run.py skills/my_workflow 验证
  7. 加到 crontab，之后执行零 AI 成本

用法：
  python run.py harness/agent -- --goal "提取这个网页里的表格数据" --dry-run
  python run.py harness/agent -- --goal "提取这个网页里的表格数据"
  python run.py harness/agent -- --goal "帮我发一条飞书圈子帖子" --sop sops/my_task.md
  python run.py harness/agent -- --goal "提取这个网页里的表格数据" --export skills/extract_daily.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.llm import generate
from core.browser import BrowserManager
from core.logger import SkillLogger
from core.agent import run_browser, run_desktop

# ── 技能注册表 ────────────────────────────────────────────────────────────────
# type 决定用哪种 subagent；hint 是给 subagent 的上下文提示
SKILL_REGISTRY = {
    "extract_table": {
        "type": "browser",
        "description": "从网页 HTML 表格提取数据并返回",
        "hint": "目标 URL 在 goal 中指定；用 browser_evaluate 提取 table 内容",
    },
    "feishu_post": {
        "type": "desktop",
        "description": "向飞书圈子发帖",
        "hint": "飞书已在桌面端运行；先截图找到导航图标，点击进入圈子，找到发帖框填入内容，选择版块后点击发布",
    },
    "feishu_approve": {
        "type": "desktop",
        "description": "在飞书 App 中批量处理待审批单（如报表申请），逐一打开并点同意",
        "hint": (
            "飞书已在桌面端运行；点击左侧导航栏「审批」图标（或从消息通知进入）进入「待我审批」列表\n"
            "找到目标类型的审批单，点击进入详情，阅读申请内容后点击「同意」按钮\n"
            "如弹出确认框，点击确认；返回列表，重复直到没有该类型的待审批单\n"
            "审批单类型名称由 goal 中指定，需精确匹配"
        ),
    },
}


# ── 规划 ──────────────────────────────────────────────────────────────────────

def plan(goal: str) -> list[dict]:
    """用 LLM 把目标分解成 subagent 调用序列。JSON 解析失败时自动重试一次。"""
    registry_desc = json.dumps(
        {k: {"description": v["description"]} for k, v in SKILL_REGISTRY.items()},
        ensure_ascii=False,
        indent=2,
    )
    prompt = f"""你是 RPA 任务规划器。将用户目标分解为子任务序列。

可用技能：
{registry_desc}

用户目标：{goal}

返回 JSON 数组，每项格式：
{{
  "skill": "技能名",
  "goal": "这个子任务的具体目标（给 subagent 的完整指令）",
  "parallel": false,
  "label": "一句话说明"
}}

规则：
- parallel=true 的相邻任务会并发执行，浏览器任务共享同一 Chrome 实例，不要并发
- goal 字段要足够具体，subagent 不看其他上下文，只靠这一句话完成任务
- 只返回合法 JSON 数组，不要解释"""

    last_err = ""
    for attempt in range(1, 3):
        response = generate(prompt, max_tokens=1024)
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if not match:
            last_err = f"未找到 JSON 数组，原始响应：{response[:200]}"
            continue
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            last_err = f"JSON 解析失败：{e}，片段：{match.group()[:200]}"
    raise ValueError(f"规划失败（已重试 2 次）：{last_err}")


# ── 执行 ──────────────────────────────────────────────────────────────────────

async def _run_task(task: dict, log: SkillLogger) -> dict:
    """为一个子任务启动对应的 subagent，失败时带错误上下文自动重试一次。"""
    skill_name = task["skill"]
    label = task.get("label", skill_name)
    MAX_ATTEMPTS = 2

    if skill_name not in SKILL_REGISTRY:
        return {"skill": skill_name, "label": label, "status": "error",
                "error": f"未知技能：{skill_name}"}

    spec = SKILL_REGISTRY[skill_name]
    base_goal = task["goal"]
    if spec.get("hint"):
        base_goal += f"\n\n技术提示：\n{spec['hint']}"

    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        full_goal = base_goal
        if attempt > 1:
            full_goal += f"\n\n⚠️ 上次尝试失败，原因：{last_error}\n请换一种方式重试。"

        retry_tag = f" (重试 {attempt}/{MAX_ATTEMPTS})" if attempt > 1 else ""
        log.step(f"▶ {label}{retry_tag}")
        print(f"  ▶ [{skill_name}] {label}{retry_tag}", flush=True)

        try:
            if spec["type"] == "browser":
                page = await BrowserManager.new_page()
                try:
                    result = await run_browser(full_goal, page)
                finally:
                    await page.close()
            else:
                result = await run_desktop(full_goal)
        except Exception as e:
            result = {"status": "error", "error": f"{type(e).__name__}: {e}"}

        if result["status"] == "ok":
            summary = str(result.get("result", ""))[:100]
            log.step(f"✅ {label}: {summary}")
            print(f"  ✅ [{skill_name}] {label}", flush=True)
            return {"skill": skill_name, "label": label, **result}

        last_error = result.get("error", "未知错误")
        print(f"  ❌ [{skill_name}] {label}: {last_error[:200]}", flush=True)

    log.step(f"❌ {label}: {last_error[:100]}")
    return {"skill": skill_name, "label": label, "status": "error", "error": last_error}


async def _execute_plan(tasks: list[dict], log: SkillLogger) -> list[dict]:
    """按规划顺序执行，parallel=true 的相邻任务并发（各自独立 page，无共享）。"""
    results = []
    group: list[dict] = []

    async def flush_group():
        if not group:
            return
        group_results = await asyncio.gather(*[_run_task(t, log) for t in group])
        results.extend(group_results)
        group.clear()

    for task in tasks:
        if task.get("parallel"):
            group.append(task)
        else:
            await flush_group()
            results.append(await _run_task(task, log))

    await flush_group()
    return results


# ── SOP 加载 ──────────────────────────────────────────────────────────────────

def _load_sop(sop_path: str) -> str:
    path = Path(sop_path)
    if not path.exists():
        raise FileNotFoundError(f"SOP 文件不存在：{sop_path}")
    return path.read_text(encoding="utf-8")


def _verify_and_confirm(sop: str) -> bool:
    """
    执行后截图验证。返回 True=继续，False=终止。
    失败时暂停交互，非交互模式（MCP subprocess）默认继续。
    """
    from core.verify import VerifyContext

    ctx = VerifyContext()
    print("\n🔍 正在截图验证结果...", flush=True)

    try:
        shot = ctx.desktop_screenshot()
        verdict = ctx.judge(sop, shot)
    except Exception as e:
        print(f"⚠️  verify 出错，跳过：{e}", flush=True)
        return True

    if verdict.ok:
        print(f"✅ verify 通过：{verdict.reason}", flush=True)
        return True

    print(f"\n⚠️  verify 未通过：{verdict.reason}", flush=True)
    print(f"   截图：{verdict.screenshot}", flush=True)

    try:
        choice = input("\n选择操作：[c] 忽略继续  [q] 终止  > ").strip().lower()
    except EOFError:
        print("（非交互模式，默认继续）", flush=True)
        choice = "c"

    if choice == "q":
        print("已终止。", flush=True)
        return False
    return True


# ── 固化导出 ──────────────────────────────────────────────────────────────────

def export_plan(goal: str, tasks: list[dict], output_path: str) -> None:
    """把规划结果导出为可编辑的骨架 Skill 脚本。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    skill_name = path.stem

    lines = [
        f'"""',
        f'[自动生成] 从 Harness 计划固化',
        f'原始目标：{goal}',
        f'',
        f'固化步骤：',
        f'  1. 把每个 TODO 替换成确定性 Playwright/桌面代码',
        f'  2. python run.py {path.with_suffix("").as_posix().replace(str(Path.cwd()) + "/", "")} 验证',
        f'  3. sh tools/cron_helper.sh {path.with_suffix("").as_posix()} "0 9 * * 1-5"',
        f'"""',
        f'',
        f'import asyncio',
        f'from core.browser import open_page',
        f'from core.logger import SkillLogger',
        f'',
        f'',
        f'async def main():',
        f'    log = SkillLogger("{skill_name}")',
        f'',
    ]

    for i, task in enumerate(tasks, 1):
        skill = task.get("skill", "unknown")
        label = task.get("label", "")
        goal_text = task.get("goal", "")
        spec = SKILL_REGISTRY.get(skill, {})
        task_type = spec.get("type", "browser")
        hint = spec.get("hint", "")

        lines += [
            f'    # ── 步骤 {i}：{label} ──',
            f'    # skill: {skill}  type: {task_type}',
            f'    # 目标：{goal_text[:120]}',
        ]
        if hint:
            first_hint_line = hint.splitlines()[0]
            lines.append(f'    # 提示：{first_hint_line}')

        if task_type == "browser":
            lines += [
                f'    # TODO: 替换为确定性 Playwright 脚本',
                f'    # async with open_page("URL") as page:',
                f'    #     await page.click("...")',
                f'    pass',
                f'',
            ]
        else:
            lines += [
                f'    # TODO: 替换为确定性桌面自动化（pyautogui / desktop.py）',
                f'    pass',
                f'',
            ]

    lines += [
        f'    log.finish()',
        f'',
        f'',
        f'if __name__ == "__main__":',
        f'    asyncio.run(main())',
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 骨架脚本已生成：{path}", flush=True)
    print(f"   下一步：打开文件，把各步骤的 TODO 替换成确定性代码", flush=True)


# ── 入口 ──────────────────────────────────────────────────────────────────────

async def run(goal: str, dry_run: bool = False, export: str = "", sop: str = "") -> list[dict]:
    log = SkillLogger("harness/agent")
    log.step(f"目标：{goal}")

    tasks = plan(goal)
    log.step(f"规划完成，共 {len(tasks)} 步")

    print(f"\n📋 执行计划（{len(tasks)} 步）：", flush=True)
    for i, t in enumerate(tasks, 1):
        hint = " [可并发]" if t.get("parallel") else ""
        print(f"  {i}. [{t.get('skill')}] {t.get('label', '')}{hint}", flush=True)
        print(f"     目标：{t.get('goal', '')[:100]}", flush=True)

    if export:
        export_plan(goal, tasks, export)
        log.finish({"export": export, "plan": tasks})
        return tasks

    if dry_run:
        print("\nDry-run 模式，不执行。", flush=True)
        log.finish({"dry_run": True, "plan": tasks})
        return tasks

    print(f"\n🚀 启动 Subagent 执行...\n", flush=True)

    try:
        results = await _execute_plan(tasks, log)
    finally:
        await BrowserManager.close()

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n{'='*40}", flush=True)
    print(f"完成：{ok}/{len(results)} 步成功", flush=True)
    for r in results:
        icon = "✅" if r["status"] == "ok" else "❌"
        print(f"  {icon} {r['label']}: {r.get('result', r.get('error', ''))[:120]}", flush=True)

    if sop:
        sop_content = _load_sop(sop)
        should_continue = _verify_and_confirm(sop_content)
        if not should_continue:
            log.finish({"ok": ok, "total": len(results), "verify": "terminated"})
            sys.exit(1)

    log.finish({"ok": ok, "total": len(results), "results": results})
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RPA Harness Agent")
    parser.add_argument("--goal", required=True, help="高层目标，自然语言描述")
    parser.add_argument("--dry-run", action="store_true", help="只规划，不执行")
    parser.add_argument("--export", default="", metavar="PATH",
                        help="规划后导出骨架脚本（如 skills/my_workflow.py），不执行")
    parser.add_argument("--sop", default="", metavar="PATH",
                        help="SOP 文档路径（.md/.txt），执行后截图验证结果是否符合规范")

    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1:]
    except ValueError:
        argv = sys.argv[1:]

    args = parser.parse_args(argv)
    asyncio.run(run(args.goal, args.dry_run, args.export, args.sop))


if __name__ == "__main__":
    main()
