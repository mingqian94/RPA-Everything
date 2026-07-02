"""
Skill 生成器：截图 + 自然语言描述 → 自动生成 Skill 代码

用法：
  python tools/generate_skill.py

交互流程：
  1. 在已登录的 Chrome 中打开目标页面
  2. 运行本工具，输入想要自动化的操作描述
  3. 工具截图当前页面，发给 Claude 理解页面结构
  4. Claude 生成完整的 Skill 代码
  5. 确认后保存到 skills/ 目录
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import anthropic
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.config import get

_API_KEY = get("llm.api_key") or os.environ.get("ANTHROPIC_API_KEY")
_MODEL = "claude-sonnet-4-6"

FRAMEWORK_CONTEXT = """
你是一个 RPA Skill 代码生成器。根据用户提供的页面截图和操作描述，生成符合以下框架规范的 Python Skill 代码。

## 框架规范

### 可用模块
```python
# Web 自动化（优先使用）
from core.browser import open_page      # 打开页面的异步上下文管理器
from core.logger import SkillLogger     # 执行日志
from core.config import get             # 读取配置

# AI 能力（仅在必要时使用）
from core.llm import generate, decide, find_element as llm_find_element

# 系统连接器
from connectors.feishu import send              # 飞书消息
from connectors.http import get_json, post_json # HTTP 接口
```

### Skill 结构模板
```python
\"\"\"[Showcase 或 Skills] Skill: <简短描述>\"\"\"

from core.browser import open_page
from core.logger import SkillLogger
from core.config import get

async def main():
    log = SkillLogger("<skill名称>")

    async with open_page("<URL>") as page:
        log.step("<步骤描述>")
        # 操作...

    log.finish()
```

### 元素定位规则
- 优先用文字定位：`page.click("text=按钮文字")`
- 其次用 CSS：`page.click(".class-name")`
- 避免用 XPath 和绝对坐标
- 如果选择器可能失效，加注释说明降级方案

### 代码风格
- 函数名固定为 `main`，async 函数
- 每个步骤调用 `log.step()`
- 不要 hardcode 个人信息（URL 从 config 读）
- 简洁，不过度注释
"""


async def capture_screenshot() -> str:
    """连接已登录的 Chrome，截取当前页面"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            await page.screenshot(path=tmp.name, full_page=False)
            url = page.url
            title = await page.title()
            return tmp.name, url, title
    except Exception as e:
        return None, None, str(e)


def generate_skill_code(screenshot_path: str, url: str, title: str, description: str) -> str:
    """调用 Claude 生成 Skill 代码"""
    import base64
    client = anthropic.Anthropic(api_key=_API_KEY)

    with open(screenshot_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode()

    prompt = f"""
页面信息：
- URL：{url}
- 标题：{title}

用户描述的操作：
{description}

请根据截图中的页面结构和用户描述，生成完整的 Python Skill 代码。
只输出代码，不要解释。
"""

    resp = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        system=FRAMEWORK_CONTEXT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_data}},
                {"type": "text", "text": prompt},
            ]
        }]
    )
    code = resp.content[0].text.strip()
    # 去掉 markdown 代码块标记
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])
    return code.strip()


def save_skill(code: str, skill_name: str) -> Path:
    path = ROOT / "skills" / f"{skill_name}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    return path


async def main():
    print("=" * 50)
    print("  RPA Skill 生成器")
    print("=" * 50)
    print("\n前提：Chrome 已用 --remote-debugging-port=9222 启动，")
    print("并已在浏览器中打开目标页面。\n")

    input("按 Enter 截取当前页面... ")

    screenshot_path, url, title = await capture_screenshot()
    if not screenshot_path:
        print(f"\n截图失败：{title}")
        print("请确认 Chrome 以 --remote-debugging-port=9222 启动。")
        return

    print(f"\n截图成功：{title}")
    print(f"页面：{url}\n")

    print("请描述你想自动化的操作（可以多行，输入空行结束）：")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    description = "\n".join(lines)

    if not description.strip():
        print("未输入描述，退出。")
        return

    print("\n正在生成 Skill 代码...")
    code = generate_skill_code(screenshot_path, url, title, description)

    print("\n" + "─" * 50)
    print(code)
    print("─" * 50)

    skill_name = input("\n保存为（skills/<名称>.py），输入名称（留空不保存）：").strip()
    if skill_name:
        path = save_skill(code, skill_name)
        print(f"\n已保存：{path}")
        print(f"运行：python run.py skills/{skill_name}")
    else:
        print("未保存。")

    # 清理截图临时文件
    os.unlink(screenshot_path)


if __name__ == "__main__":
    asyncio.run(main())
