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
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.llm import agent_step
from core.browser import BrowserManager
from core.logger import SkillLogger
from core.agent import run_android, run_browser, run_desktop
from core.capabilities import build_skill_registry
from harness.routes import annotate_tasks, route_for_skill, route_for_trace_result
from harness.trace import export_trace_json

# ── 技能注册表 ────────────────────────────────────────────────────────────────
# type 决定用哪种 subagent；hint 是给 subagent 的上下文提示
SKILL_REGISTRY = {
    "extract_table": {
        "type": "browser",
        "description": "从网页 HTML 表格提取数据并返回",
        "hint": "目标 URL 在 goal 中指定；用 browser_evaluate 提取 table 内容",
    },
    "browser_explore": {
        "type": "browser",
        "description": "探索一个网页或浏览器系统，完成点击、输入、截图、文本/表格提取等通用浏览器任务",
        "hint": (
            "优先使用 DOM/CSS/文本定位；每个关键操作后截图或提取文本确认结果；"
            "如果目标是沉淀 Skill，记录稳定 selector 和必要前置登录状态"
        ),
    },
    "desktop_explore": {
        "type": "desktop",
        "description": "探索本机桌面应用，完成截图、点击、输入、快捷键等通用桌面任务",
        "hint": (
            "先截图确认当前窗口和目标元素；中文输入走剪贴板；关键结果要截图确认。"
            "如果是长期复用流程，优先沉淀成模板匹配或确定性窗口操作，不要依赖一次性坐标"
        ),
    },
    "android_explore": {
        "type": "android",
        "description": "探索已连接 Android 手机，完成设备发现、截图、点击、滑动、按键、输入和文件推送",
        "hint": (
            "先调用 android_devices / android_diagnostics 确认设备在线；"
            "优先使用 0~1 屏幕比例坐标，避免写死像素；"
            "中文、emoji、换行文本用 android_type unicode=true；"
            "真实外部副作用（发布/发送/付款等）完成后只标记待确认，除非有明确成功信号"
        ),
    },
    "android_diagnostics": {
        "type": "android",
        "description": "检查 Android 自动化前置条件：ADB 连接、截图、可选输入注入、文件推送等",
        "hint": (
            "先列出设备，再运行 android_diagnostics；"
            "默认不要启用输入检查，除非用户明确允许，因为 include_input_check 会发送 HOME"
        ),
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

# Final planner catalog: built-ins plus auto-discovered showcase/skills.
SKILL_REGISTRY = build_skill_registry()


def _registry_for_planner() -> dict:
    out = {}
    for name, spec in SKILL_REGISTRY.items():
        item = {
            "description": spec.get("description", ""),
            "hint": spec.get("hint", ""),
            "type": spec.get("type", ""),
            "side_effect_level": spec.get("side_effect_level", "unknown"),
        }
        if spec.get("args_schema"):
            item["args_schema"] = spec["args_schema"]
            item["args_rule"] = (
                "For skill:* tasks, fill task.args exactly as CLI tokens after `python run.py <skill> --`. "
                "Include every required option and respect defaults/types."
            )
        out[name] = item
    return out


def _provided_option_names(args: list[str]) -> set[str]:
    names: set[str] = set()
    for arg in args:
        if arg.startswith("--"):
            names.add(arg.split("=", 1)[0])
    return names


def _validate_skill_args(spec: dict, args: list[str]) -> str:
    schema = spec.get("args_schema") or []
    provided = _provided_option_names(args)
    for item in schema:
        if not item.get("required"):
            continue
        names = [n for n in item.get("names", []) if n.startswith("--")]
        if names and not any(n in provided for n in names):
            return f"missing required arg for {spec.get('path')}: one of {names}"
    valid = {n for item in schema for n in item.get("names", []) if n.startswith("--")}
    unknown = sorted(n for n in provided if valid and n not in valid)
    if unknown:
        return f"unknown arg for {spec.get('path')}: {unknown}"
    return ""


# ── 规划 ──────────────────────────────────────────────────────────────────────

_PLAN_TOOL = {
    "name": "submit_plan",
    "description": "提交任务规划结果。",
    "input_schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string", "description": "技能名，必须来自可用技能列表"},
                        "goal": {"type": "string", "description": "子任务的具体目标（给 subagent 的完整指令，subagent 只看这一句话）"},
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "仅 skill:* 能力使用：传给 `python run.py <skill> --` 后面的 CLI 参数",
                        },
                        "parallel": {"type": "boolean", "description": "与相邻任务并发执行。浏览器任务共享同一 Chrome 实例，不要并发"},
                        "label": {"type": "string", "description": "一句话说明"},
                    },
                    "required": ["skill", "goal", "label"],
                },
            },
        },
        "required": ["tasks"],
    },
}


def plan(goal: str) -> list[dict]:
    """用 LLM 把目标分解成 subagent 调用序列。
    通过强制 tool use 拿结构化输出，不再从自由文本里正则抠 JSON。"""
    registry_desc = json.dumps(_registry_for_planner(), ensure_ascii=False, indent=2)
    prompt = f"""你是 RPA Harness 任务规划器。将用户目标分解为子任务序列，调用 submit_plan 提交。

规划原则：
- skill 必须来自可用技能列表，不要发明技能名。
- 应用目标先检查可用技能中是否已有 `showcase/app/integration/` 的对应直连 Skill；存在时优先选它，直接用 MCP/CLI/API 完成并验证结果，不要打开窗口、截图或做视觉识别。不存在时不能假设应用有直连能力，再考虑 `showcase/app/desktop/` 或 desktop_*。
- 目标明确属于网页/浏览器时选 browser_*；属于本机应用时选 desktop_*；属于手机/Android/ADB 时选 android_*。
- 用户目标是先确认环境、设备、权限是否可用时，优先规划 diagnostics 类任务。
- 真实外部副作用场景（发布、发送、审批、付款等）要在 goal 中要求执行后验证；没有确定成功信号时说明“待确认”。
- 浏览器任务共享 Chrome，不要并发；桌面和 Android 操作通常也不要并发，除非目标明确是互不影响的检查。

可用技能：
{registry_desc}

用户目标：{goal}"""

    resp = agent_step(
        [{"role": "user", "content": prompt}],
        tools=[_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_plan"},
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "submit_plan":
            tasks = block.input.get("tasks", [])
            if tasks:
                return tasks
    raise ValueError(f"规划失败：模型未返回有效计划（stop_reason={resp.stop_reason}）")


# ── 执行 ──────────────────────────────────────────────────────────────────────

async def _run_saved_skill(spec: dict, task: dict) -> dict:
    """Run a discovered showcase/skills script through run.py."""
    skill_path = spec.get("path")
    if not skill_path:
        return {"status": "error", "error": "skill capability is missing path"}

    args = task.get("args") or []
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        return {"status": "error", "error": "skill args must be a list of strings"}
    arg_error = _validate_skill_args(spec, args)
    if arg_error:
        return {"status": "error", "error": arg_error}

    cmd = [sys.executable, "run.py", skill_path]
    if args:
        cmd += ["--", *args]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    stdout = stdout_b.decode("utf-8", "replace")
    stderr = stderr_b.decode("utf-8", "replace")
    if proc.returncode == 0:
        return {"status": "ok", "result": stdout.strip() or f"Skill completed: {skill_path}"}
    return {
        "status": "error",
        "error": (stderr.strip() or stdout.strip() or f"Skill failed with exit code {proc.returncode}")[:4000],
    }


def _external_commit_requested(spec: dict, task: dict) -> bool:
    level = spec.get("side_effect_level", "unknown")
    args = task.get("args") or []
    if level == "external_commit":
        return True
    return level == "external_draft" and any(a in {"--confirm", "--confirm-post", "--publish"} for a in args)


async def _run_task(
    task: dict,
    log: SkillLogger,
    confirm_external: bool = False,
    handoff_on_login: bool = False,
) -> dict:
    """为一个子任务启动对应的 subagent，失败时带错误上下文自动重试一次。"""
    skill_name = task["skill"]
    label = task.get("label", skill_name)
    MAX_ATTEMPTS = 2

    if skill_name not in SKILL_REGISTRY:
        return {"skill": skill_name, "label": label, "status": "error",
                "error": f"未知技能：{skill_name}"}

    spec = SKILL_REGISTRY[skill_name]
    route = task.get("route") or route_for_skill(skill_name, spec)
    if _external_commit_requested(spec, task) and not confirm_external:
        return {
            "skill": skill_name,
            "label": label,
            "route": route,
            "status": "error",
            "error": (
                "该任务可能产生真实外部副作用。请人工确认后使用 "
                "--confirm-external 再执行；或去掉最终发布/审批/发送参数。"
            ),
        }
    max_attempts = 1 if spec.get("type") == "skill" else MAX_ATTEMPTS
    base_goal = task["goal"]
    if spec.get("hint"):
        base_goal += f"\n\n技术提示：\n{spec['hint']}"
    base_goal += (
        f"\n\n已选自动化路线：{route['selected']}。"
        f"降级顺序：{' -> '.join(route['fallbacks'])}。"
        f"视觉识别规则：{route['vision']}"
    )

    last_error = ""
    for attempt in range(1, max_attempts + 1):
        full_goal = base_goal
        trace: list[dict] = []
        if attempt > 1:
            full_goal += f"\n\n⚠️ 上次尝试失败，原因：{last_error}\n请换一种方式重试。"

        retry_tag = f" (重试 {attempt}/{max_attempts})" if attempt > 1 else ""
        log.step(f"▶ {label}{retry_tag}")
        print(f"  ▶ [{skill_name}] {label}{retry_tag}", flush=True)

        try:
            if spec["type"] == "browser":
                page = await BrowserManager.new_page()
                try:
                    result = await run_browser(
                        full_goal,
                        page,
                        trace=trace,
                        handoff_on_login=handoff_on_login,
                    )
                    result.setdefault("trace", trace)
                finally:
                    await page.close()
            elif spec["type"] == "desktop":
                result = await run_desktop(full_goal, trace=trace)
                result.setdefault("trace", trace)
            elif spec["type"] == "android":
                result = await run_android(full_goal, trace=trace)
                result.setdefault("trace", trace)
            elif spec["type"] == "skill":
                result = await _run_saved_skill(spec, task)
            else:
                result = {"status": "error", "error": f"不支持的技能类型：{spec['type']}"}
        except Exception as e:
            result = {"status": "error", "error": f"{type(e).__name__}: {e}"}

        if result["status"] == "ok":
            summary = str(result.get("result", ""))[:100]
            log.step(f"✅ {label}: {summary}")
            print(f"  ✅ [{skill_name}] {label}", flush=True)
            return {"skill": skill_name, "label": label, "route": route, **result}

        if result["status"] == "needs_human_step":
            handoff = result.get("human_step", {})
            message = handoff.get("message", "需要人工完成当前步骤")
            log.step(f"⏸ {label}: {message}")
            print(f"  ⏸ [{skill_name}] {label}: {message}", flush=True)
            return {"skill": skill_name, "label": label, "route": route, **result}

        last_error = result.get("error", "未知错误")
        print(f"  ❌ [{skill_name}] {label}: {last_error[:200]}", flush=True)

    log.step(f"❌ {label}: {last_error[:100]}")
    return {"skill": skill_name, "label": label, "route": route, "status": "error", "error": last_error}


async def _execute_plan(
    tasks: list[dict],
    log: SkillLogger,
    confirm_external: bool = False,
    handoff_on_login: bool = False,
) -> list[dict]:
    """按规划顺序执行，parallel=true 的相邻任务并发（各自独立 page，无共享）。"""
    results = []
    group: list[dict] = []

    async def flush_group():
        if not group:
            return
        group_results = await asyncio.gather(*[
            _run_task(t, log, confirm_external, handoff_on_login) for t in group
        ])
        results.extend(group_results)
        group.clear()

    for task in tasks:
        if task.get("parallel"):
            group.append(task)
        else:
            await flush_group()
            results.append(await _run_task(task, log, confirm_external, handoff_on_login))

    await flush_group()
    return results


# ── SOP 加载 ──────────────────────────────────────────────────────────────────

def _load_sop(sop_path: str) -> str:
    path = Path(sop_path)
    if not path.exists():
        raise FileNotFoundError(f"SOP 文件不存在：{sop_path}")
    return path.read_text(encoding="utf-8")


async def _verify_and_confirm(sop: str, tasks: list[dict]) -> bool:
    """
    执行后截图验证。返回 True=继续，False=终止。
    浏览器类任务截当前页面，桌面类任务截全屏。
    失败时暂停交互，非交互模式（MCP subprocess）默认继续。
    """
    from core.verify import VerifyContext

    ctx = VerifyContext()
    print("\n🔍 正在截图验证结果...", flush=True)

    task_types = {SKILL_REGISTRY.get(t.get("skill"), {}).get("type") for t in tasks}
    try:
        if "browser" in task_types:
            page = await BrowserManager.current_page()
            shot = await ctx.browser_screenshot(page)
        elif "android" in task_types:
            import os
            from core.android import AndroidDevice

            fd, shot = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            AndroidDevice().screencap_to(shot)
        else:
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

def _export_skill_readme(goal: str, tasks: list[dict], path: Path) -> Path:
    """Write a review guide beside generated code without copying secrets."""
    readme_path = path.with_name(f"{path.stem}.README.md")
    risky_tasks = []
    for task in tasks:
        spec = SKILL_REGISTRY.get(task.get("skill", ""), {})
        if spec.get("side_effect_level") in {"external_draft", "external_commit", "unknown"}:
            risky_tasks.append(task.get("label") or task.get("skill") or "unnamed step")

    lines = [
        f"# {path.stem}",
        "",
        "This guide was generated with the Skill skeleton. Review the Python file before running it.",
        "",
        "## Goal",
        "",
        goal,
        "",
        "## Run",
        "",
        "```bash",
        f"python run.py {path.as_posix()}",
        "```",
        "",
        "## Before first run",
        "",
        "- Replace every `TODO` with deterministic selectors or local automation code.",
        "- Put API keys, passwords, cookies, and private URLs in `config.yaml` or environment variables, never in this Skill.",
        "- Inspect logs or output files before scheduling the Skill.",
    ]
    if risky_tasks:
        lines += ["", "## External-action guard", "", "This plan may prepare or commit an action in another system:"]
        lines.extend(f"- {label}" for label in risky_tasks)
        lines += [
            "",
            "Keep final publish/send/approve/delete steps separate. Use docs/external-action-confirmation.zh-CN.md before allowing a real action.",
        ]
    lines += ["", "## Generated plan", ""]
    for index, task in enumerate(tasks, 1):
        route = task.get("route") or route_for_skill(
            task.get("skill", ""), SKILL_REGISTRY.get(task.get("skill", ""), {})
        )
        lines.append(f"{index}. {task.get('label') or task.get('goal') or task.get('skill', 'unnamed step')}")
        lines.append(f"   Route: {route['selected']} -> {', '.join(route['fallbacks'])}")
    lines.append("")
    readme_path.write_text("\n".join(lines), encoding="utf-8")
    return readme_path


def export_plan(goal: str, tasks: list[dict], output_path: str) -> None:
    """把规划结果导出为可编辑的骨架 Skill 脚本。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    skill_name = path.stem

    lines = [
        '"""',
        '[自动生成] 从 Harness 计划固化',
        f'原始目标：{goal}',
        '',
        '固化步骤：',
        '  1. 把每个 TODO 替换成确定性 Playwright / desktop.py / android.py 代码',
        f'  2. python run.py {path.with_suffix("").as_posix().replace(str(Path.cwd()) + "/", "")} 验证',
        f'  3. sh tools/cron_helper.sh {path.with_suffix("").as_posix()} "0 9 * * 1-5"',
        '"""',
        '',
        'import asyncio',
        'from core.browser import open_page',
        'from core.android import AndroidDevice',
        'from core.logger import SkillLogger',
        '',
        '',
        'async def main():',
        f'    log = SkillLogger("{skill_name}")',
        '',
    ]

    for i, task in enumerate(tasks, 1):
        skill = task.get("skill", "unknown")
        label = task.get("label", "")
        goal_text = task.get("goal", "")
        spec = SKILL_REGISTRY.get(skill, {})
        task_type = spec.get("type", "browser")
        hint = spec.get("hint", "")
        route = task.get("route") or route_for_skill(skill, spec)

        lines += [
            f'    # ── 步骤 {i}：{label} ──',
            f'    # skill: {skill}  type: {task_type}',
            f'    # 目标：{goal_text[:120]}',
            f"    # route: {route['selected']} -> {', '.join(route['fallbacks'])}",
        ]
        if hint:
            first_hint_line = hint.splitlines()[0]
            lines.append(f'    # 提示：{first_hint_line}')

        if task_type == "browser":
            lines += [
                '    # TODO: 替换为确定性 Playwright 脚本',
                '    # async with open_page("URL") as page:',
                '    #     await page.click("...")',
                '    pass',
                '',
            ]
        elif task_type == "desktop":
            lines += [
                '    # TODO: 替换为确定性桌面自动化（pyautogui / desktop.py）',
                '    pass',
                '',
            ]
        elif task_type == "android":
            lines += [
                '    # TODO: 替换为确定性 Android 自动化（ADB / android.py）',
                '    # dev = AndroidDevice()',
                '    # dev.ensure_online()',
                '    # dev.screencap_to("logs/android_before.png")',
                '    # dev.tap_ratio(0.5, 0.5)',
                '    # 真实外部副作用完成后，如无明确成功信号，请记录为“待确认”',
                '    pass',
                '',
            ]
        elif task_type == "skill":
            skill_path = spec.get("path", skill)
            args = task.get("args") or []
            lines += [
                '    # TODO: 这里来自已固化 Skill，可直接调用或内联其关键逻辑',
                f'    # python run.py {skill_path} -- {" ".join(args)}',
                '    pass',
                '',
            ]
        else:
            lines += [
                f'    # TODO: 未知技能类型 {task_type!r}，请手工补齐',
                '    pass',
                '',
            ]

    lines += [
        '    log.finish()',
        '',
        '',
        'if __name__ == "__main__":',
        '    asyncio.run(main())',
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    readme_path = _export_skill_readme(goal, tasks, path)
    print(f"\n📄 骨架脚本已生成：{path}", flush=True)
    print(f"   使用说明：{readme_path}", flush=True)
    print("   下一步：打开文件，把各步骤的 TODO 替换成确定性代码", flush=True)


def export_trace(goal: str, results: list[dict], output_path: str) -> None:
    """Export executed tool calls as an editable first-draft Skill."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    skill_name = path.stem
    lines = [
        '"""',
        "[自动生成] Harness 执行轨迹初稿",
        f"原始目标：{goal}",
        "",
        "请 review 后再用于生产：桌面坐标和真实外部副作用步骤尤其需要人工确认。",
        '"""',
        "",
        "import asyncio",
        "import subprocess",
        "import sys",
        "from core.android import AndroidDevice",
        "from core.browser import open_page",
        "from core.desktop import click as desktop_click, hotkey as desktop_hotkey, type_text as desktop_type",
        "from core.logger import SkillLogger",
        "",
        "",
        "async def main():",
        f'    log = SkillLogger("{skill_name}")',
    ]

    browser_started = False
    android_started = False
    for result in results:
        lines.append("")
        lines.append(f"    # ── {result.get('label', result.get('skill', 'step'))} ──")
        route = route_for_trace_result(result)
        lines.append(f"    # route: {route['selected']} -> {', '.join(route['fallbacks'])}")
        if result.get("skill", "").startswith("skill:"):
            spec = SKILL_REGISTRY.get(result["skill"], {})
            skill_path = spec.get("path", result["skill"].removeprefix("skill:"))
            lines.append(f'    subprocess.run([sys.executable, "run.py", "{skill_path}"], check=True)')
            continue

        for item in result.get("trace", []):
            tool = item.get("tool")
            args = item.get("args", {})
            if item.get("is_error"):
                lines.append(f"    # skipped failed tool call: {tool} {args!r}")
                continue
            if tool and tool.startswith("browser_") and tool != "browser_navigate" and not browser_started:
                lines.append("    page_ctx = open_page(None)")
                lines.append("    page = await page_ctx.__aenter__()")
                browser_started = True
            if tool == "browser_navigate":
                lines.append(f'    page_ctx = open_page({args.get("url", "")!r})')
                lines.append("    page = await page_ctx.__aenter__()")
                browser_started = True
            elif tool == "browser_click":
                if args.get("selector"):
                    lines.append(f'    await page.click({args["selector"]!r})')
                elif args.get("text"):
                    lines.append(f'    await page.click("text={args["text"]}")')
            elif tool == "browser_type":
                lines.append(f'    await page.fill({args.get("selector", "")!r}, {args.get("text", "")!r})')
            elif tool == "browser_evaluate":
                lines.append(f'    await page.evaluate({args.get("js", "")!r})')
            elif tool == "android_tap":
                if not android_started:
                    lines.append("    dev = AndroidDevice()")
                    android_started = True
                if "rx" in args and "ry" in args:
                    lines.append(f'    dev.tap_ratio({float(args["rx"])!r}, {float(args["ry"])!r})')
                else:
                    lines.append(f'    dev.tap({int(args.get("x", 0))}, {int(args.get("y", 0))})')
            elif tool == "android_tap_element":
                if not android_started:
                    lines.append("    dev = AndroidDevice()")
                    android_started = True
                lines.append(
                    "    dev.tap_ui_node("
                    f'text={args.get("text", "")!r}, '
                    f'resource_id={args.get("resource_id", "")!r}, '
                    f'content_desc={args.get("content_desc", "")!r}, '
                    f'exact={bool(args.get("exact", False))!r})'
                )
            elif tool == "android_swipe":
                if not android_started:
                    lines.append("    dev = AndroidDevice()")
                    android_started = True
                if all(k in args for k in ("rx1", "ry1", "rx2", "ry2")):
                    lines.append(
                        "    dev.swipe_ratio("
                        f'{float(args["rx1"])!r}, {float(args["ry1"])!r}, '
                        f'{float(args["rx2"])!r}, {float(args["ry2"])!r}, '
                        f'{int(args.get("duration_ms", 300))})'
                    )
                else:
                    lines.append(
                        "    dev.swipe("
                        f'{int(args.get("x1", 0))}, {int(args.get("y1", 0))}, '
                        f'{int(args.get("x2", 0))}, {int(args.get("y2", 0))}, '
                        f'{int(args.get("duration_ms", 300))})'
                    )
            elif tool == "android_key":
                if not android_started:
                    lines.append("    dev = AndroidDevice()")
                    android_started = True
                lines.append(f'    dev.key({args.get("keycode", "")!r})')
            elif tool == "android_type":
                if not android_started:
                    lines.append("    dev = AndroidDevice()")
                    android_started = True
                lines.append(
                    f'    dev.input_text({args.get("text", "")!r}, '
                    f'unicode={bool(args.get("unicode"))!r}, '
                    f'restore_ime={bool(args.get("restore_ime", True))!r})'
                )
            elif tool == "desktop_click":
                lines.append(f'    desktop_click({int(args.get("x", 0))}, {int(args.get("y", 0))})  # TODO: prefer template matching')
            elif tool == "desktop_type":
                lines.append(f'    desktop_type({args.get("text", "")!r})')
            elif tool == "desktop_hotkey":
                keys = args.get("keys", [])
                lines.append(f"    desktop_hotkey(*{keys!r})")
            else:
                lines.append(f"    # TODO: review tool call: {tool} {args!r}")

    if browser_started:
        lines.append("    await page_ctx.__aexit__(None, None, None)")
    lines += [
        '    log.finish({"exported_from_trace": True})',
        "",
        "",
        'if __name__ == "__main__":',
        "    asyncio.run(main())",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 执行轨迹脚本已生成：{path}", flush=True)


# ── 入口 ──────────────────────────────────────────────────────────────────────

async def run(
    goal: str,
    dry_run: bool = False,
    export: str = "",
    sop: str = "",
    confirm_external: bool = False,
    export_trace_path: str = "",
    trace_json_path: str = "",
    handoff_on_login: bool = False,
) -> list[dict]:
    log = SkillLogger("harness/agent")
    log.step(f"目标：{goal}")

    tasks = annotate_tasks(plan(goal), SKILL_REGISTRY)
    log.step(f"规划完成，共 {len(tasks)} 步")

    print(f"\n📋 执行计划（{len(tasks)} 步）：", flush=True)
    for i, t in enumerate(tasks, 1):
        hint = " [可并发]" if t.get("parallel") else ""
        print(f"  {i}. [{t.get('skill')}] {t.get('label', '')}{hint}", flush=True)
        print(f"     目标：{t.get('goal', '')[:100]}", flush=True)
        route = t["route"]
        print(f"     路线：{route['selected']} -> {', '.join(route['fallbacks'])}", flush=True)

    if export:
        export_plan(goal, tasks, export)
        log.finish({"export": export, "plan": tasks})
        return tasks

    if dry_run:
        print("\nDry-run 模式，不执行。", flush=True)
        log.finish({"dry_run": True, "plan": tasks})
        return tasks

    print("\n🚀 启动 Subagent 执行...\n", flush=True)

    try:
        results = await _execute_plan(tasks, log, confirm_external, handoff_on_login)
    finally:
        await BrowserManager.close()

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n{'='*40}", flush=True)
    handoffs = sum(1 for r in results if r["status"] == "needs_human_step")
    print(f"完成：{ok}/{len(results)} 步成功", flush=True)
    if handoffs:
        print(f"待人工交接：{handoffs} 步", flush=True)
    for r in results:
        icon = "✅" if r["status"] == "ok" else ("⏸" if r["status"] == "needs_human_step" else "❌")
        detail = r.get("result", r.get("error", ""))
        if r["status"] == "needs_human_step":
            detail = r.get("human_step", {}).get("message", "需要人工完成当前步骤")
        print(f"  {icon} {r['label']}: {detail[:120]}", flush=True)

    if sop:
        sop_content = _load_sop(sop)
        should_continue = await _verify_and_confirm(sop_content, tasks)
        if not should_continue:
            log.finish({"ok": ok, "total": len(results), "verify": "terminated"})
            sys.exit(1)

    if export_trace_path:
        export_trace(goal, results, export_trace_path)
    if trace_json_path:
        path = export_trace_json(goal, results, trace_json_path)
        print(f"\nTrace JSON saved: {path}", flush=True)

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
    parser.add_argument("--confirm-external", action="store_true",
                        help="允许执行可能产生真实外部副作用的发布/审批/发送类任务")
    parser.add_argument("--export-trace", default="", metavar="PATH",
                        help="执行后把工具调用轨迹导出为初版 Skill 脚本")

    parser.add_argument("--trace-json", default="", metavar="PATH",
                        help="Export replayable tool-call trace JSON after execution")
    parser.add_argument("--handoff-on-login", action="store_true",
                        help="Return needs_human_step when login/MFA is required instead of waiting for console input")

    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1:]
    except ValueError:
        argv = sys.argv[1:]

    args = parser.parse_args(argv)
    asyncio.run(run(
        args.goal,
        args.dry_run,
        args.export,
        args.sop,
        args.confirm_external,
        args.export_trace,
        args.trace_json,
        args.handoff_on_login,
    ))


if __name__ == "__main__":
    main()
