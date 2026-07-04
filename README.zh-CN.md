# RPA-Everything

[English](README.md) | **中文**

![CI](https://github.com/mingqian94/RPA-Everything/actions/workflows/ci.yml/badge.svg)

一个面向所有职场人的智能自动化框架：用自然语言描述任务，AI 帮你把重复操作变成可复用的脚本。

> **不是通用 RPA 平台**，而是"AI 写脚本、人来审核、脚本定时跑"的轻量工作流。适合需要频繁处理重复性系统操作的个人或团队。

> **AI Agent 接入**：如果你是 Claude Desktop、Codex 等桌面 Agent，请阅读 [AGENTS.md](AGENTS.md) 了解接入方式。

---

## 和同类工具的区别

| 工具 | 定位 | 问题 |
|---|---|---|
| Playwright / Selenium | 开发者写测试脚本 | 需要写代码，运营同学用不了 |
| n8n / Zapier | 无代码流程编排 | 遇到复杂 UI 操作或私有系统就断 |
| RPA 平台（UiPath 等） | 企业级录制回放 | 重，贵，AI 能力弱 |
| Claude Computer Use | AI 直接看屏幕、算坐标、操作鼠标键盘 | 每次执行都要模型重新"看懂"界面：有 token 成本，且 LLM 从截图猜坐标本身不够可靠（这个项目就踩过 Retina 屏幕坐标系不一致导致的误点击） |
| **本框架** | AI 对话生成脚本，脚本定时执行 | 探索成本高（需要 Claude API） |

**核心取舍**：用 AI 降低"写自动化脚本"的门槛，但执行时不依赖 AI——流程固化后是纯脚本，零 AI 成本、高稳定性。

### 和 Claude Computer Use 的区别

一句话：**Computer Use 是"AI 每次都亲自动手"，本框架是"AI 只出手一次（探索阶段），之后交给确定性脚本"。**

Computer Use 让模型直接看截图、自己判断坐标、自己点鼠标——这是通用能力，适合真正一次性、没法提前知道步骤的探索任务。但如果同一件事要反复做（比如每天查一次假期余额、每小时批一次审批），每次都让模型重新"看懂"界面既费 token，也不够稳：模型从截图判断坐标的精度有限，Retina 屏幕物理像素/逻辑像素不一致这类问题就是实测踩过的坑。

本框架把这个能力拆成两阶段：**探索阶段**用 AI（可以是截图分析、也可以是浏览器 DOM 操作）摸清一次操作步骤；**固化阶段**把这些步骤写成确定性脚本——桌面类优先用图像模板匹配（`core/desktop.py` 的 `locate_and_click()`）定位元素而不是让 LLM 猜坐标，浏览器类优先用 CSS/XPath 选择器而不是视觉识别。固化之后 AI 就退场了，脚本可以直接进 crontab，零 AI 成本、结果可复现、代码可 review。

真实案例对比：飞书审批自动化最初用 Harness（截图 + LLM 判断坐标点击，跟 Computer Use 是同一种模式）测试，两次都出问题——一次 API 请求卡死，一次坐标偏移点错了别的应用；换成图像模板匹配写成固定脚本后，同一批真实审批单测试 3/3 全部成功，18 秒跑完，零 AI 调用。

---

## 工作流程

```
描述任务（自然语言）
    ↓
Claude Desktop + MCP Server
    ↓  截图、操作、生成代码
确认无误 → 保存为 Skill
    ↓
python run.py <skill>   # 定时/按需执行，不再调 AI
```

---

## 架构

```
┌──────────────────────────────────────────────────┐
│              用户（对话 / 命令行）                 │
│     Claude Desktop / python run.py <skill>        │
├──────────────────────────────────────────────────┤
│           MCP Server  mcp_server.py               │
│  对话驱动：自然语言 → Claude → 调工具执行          │
│  可固化：执行完自动生成 Skill 代码保存             │
├──────────┬───────────────────┬───────────────────┤
│ Showcase │    用户自建 Skill  │   直接运行脚本     │
│ 示例精选  │  对话生成后保存    │  python run.py    │
└──────────┴───────────────────┴───────────────────┘
                      ↓
         core / connectors（通用底层）
```

---

## 目录结构

```
rpa-everything/
├── core/                    # 通用能力层（与业务无关）
│   ├── browser.py           # Web 自动化（Playwright，复用已登录 Chrome）；is_logged_in() 判断 httpOnly 会话 cookie
│   ├── intercept.py         # 拦截页面 API 响应（fetch/XHR 双 hook，用于数据靠后台请求加载的页面）
│   ├── desktop.py           # 桌面自动化（macOS: screencapture + pyautogui；Windows: pywinauto）
│   ├── llm.py               # Claude API（判断 / 生成内容 / 视觉兜底）
│   ├── agent.py             # Agentic loop（run_browser / run_desktop）
│   ├── tools.py             # 工具定义唯一来源（agentic loop 与 MCP Server 共享）
│   ├── skills.py            # Skill 发现与保存（run.py / MCP / 生成器共用）
│   ├── config.py            # 配置读取（config.yaml + 环境变量）
│   ├── logger.py            # 结构化执行日志（自动清理过期日志）
│   ├── notify.py            # 任务失败推送通知（飞书 Webhook）
│   └── verify.py            # 执行后结果验证（LLM-as-judge，截图 + SOP → ok/fail）
│
├── connectors/              # 系统连接器（按需引入）
│   ├── feishu.py            # 飞书 API
│   └── http.py              # 通用 HTTP
│
├── harness/                 # Harness Agent（高层目标 → 自动规划 + 执行）
│   └── agent.py             # LLM 规划（tool use 结构化输出）→ subagent 并发执行
│
├── showcase/                # Skill 示例库（六种技术路线各有 showcase，见 ARCHITECTURE.md）
│   ├── web/
│   │   ├── extract_table/   # 通用网页表格提取（Browser DOM）
│   │   └── click_by_vision/ # 视觉识别点击（Browser + LLM Vision）
│   ├── app/
│   │   └── template_click/  # 图像模板匹配点击（桌面路线最小示例，模板自备）
│   └── office/              # 纯文件格式操作，不需要屏幕，可跑服务器
│       ├── excel_toolkit/   # Excel 读写（openpyxl）
│       ├── ppt_generator/   # 从结构化内容生成 PPT（python-pptx）
│       └── word_report/     # 从结构化内容生成 Word 文档（python-docx）
│
├── skills/                  # 自建 Skill（可提交到仓库，也可本地私有）
│   └── feishu_project_daily.py  # 飞书项目日报（API 拦截路线，定时跑）
│
├── assets/                  # 桌面自动化用的图像模板（按系统名分子目录，自行截图放入）
├── sops/                    # SOP 文档库（用户贡献，供 Harness verify 用；自行按需添加）
│
├── tools/
│   ├── generate_skill.py    # Skill 生成器（截图 + 描述 → 代码）
│   ├── cron_helper.sh       # 生成 crontab 行（macOS / Linux）
│   ├── cron_helper.ps1      # 生成 schtasks 命令（Windows）
│   ├── start_chrome.sh      # 启动调试 Chrome（macOS）
│   └── start_chrome.bat     # 启动调试 Chrome（Windows）
│
├── logs/                    # 执行日志（自动生成，默认保留 30 天）
├── config.yaml              # 配置模板
├── mcp_server.py            # MCP Server 入口
├── run.py                   # 统一执行入口（pip install -e . 后可用 rpa 命令）
└── pyproject.toml
```

---

## 运行环境：本地 vs 服务器

不同类型的 Skill 对运行环境的要求不同：

| Skill 类型 | 典型场景 | 能否跑在服务器 | 说明 |
|---|---|---|---|
| **API 类** | 飞书 API、自定义 Webhook | ✅ 可以 | 纯 HTTP 调用，无界面依赖 |
| **Office 文件类** | Excel/PPT/Word 读写 | ✅ 可以 | 纯文件格式操作，不需要对应应用打开 |
| **浏览器类** | CRM 查询、HR 系统 | ⚠️ 需本地 Chrome | 依赖用户已登录的 Chrome 会话 |
| **桌面类** | 飞书、钉钉原生应用 | ❌ 必须本地 | 需要物理屏幕和前台窗口 |

**部署建议：**

```
定时自动化（无人值守）
  → 只用 API 类 Skill → 挂到服务器，cron 定时触发

需要操作界面
  → 跑在本地机器，或一台常开的专用机（Mac Mini / Windows 主机）
```

API 类和界面类混用时，建议把流程拆开：界面操作本地跑，结果通过 API 发出去。

---

## 支持的自动化场景

| 应用类型 | 示例 | 方案 | 模块 |
|---|---|---|---|
| **API 接口** | 飞书操作、自定义 HTTP 接口 | HTTP 直接调用 | `connectors/` |
| **Office 文件** | Excel、PPT、Word 报表/文档 | 直接读写文件格式（openpyxl / python-pptx / python-docx），不打开应用 | `showcase/office/` |
| **Web 应用** | CRM、HR 系统、教务平台 | Playwright DOM 操作 | `core/browser.py` |
| **Electron 桌面** | 飞书、钉钉桌面版 | Playwright 连调试端口 | `core/browser.py` |
| **Windows 原生应用** | 本地教务软件 | pywinauto UI Automation | `core/desktop.py` |
| **任意桌面应用（兜底）** | 飞书、钉钉等 | PyAutoGUI + 图像模板匹配定位；中文走剪贴板粘贴 | `core/desktop.py` |

### 元素定位降级链

**浏览器类：**
```
CSS/XPath 选择器  →  失败  →  Claude Vision  →  失败  →  人工确认
   毫秒级·零成本            按 token 计费          最终兜底
```

**桌面类：**
```
图像模板匹配（locate_and_click）  →  失败  →  Claude Vision 截图猜坐标  →  失败  →  人工确认
      零成本·确定性·抗小幅缩放漂移         按 token 计费，精度弱于模板匹配
```

模板匹配优先于 LLM 视觉猜坐标：样式固定的按钮/图标（同意、导航项等）截一次图存成模板
（约定放在 `assets/<系统名>/`），之后每次用 `core.desktop.locate_and_click()` 精确定位，
不需要 LLM 参与，也避免了"LLM 从截图读物理像素坐标、点击却按逻辑像素坐标解释"在 Retina
屏幕上导致的点击偏移问题（`core/desktop.py` 的 `physical_to_logical()` 已处理这层换算，
但模板匹配从根源上不依赖坐标猜测，更可靠）。

---

## 快速开始

### 1. 安装依赖

**系统依赖（Python 包之外）：**

| 依赖 | 用途 | 必须？ |
|---|---|---|
| **Google Chrome** | 浏览器类 Skill 的执行环境（复用已登录会话） | 浏览器类 Skill 必须 |
| Python 3.11+ | 运行框架 | 必须 |

Chrome 下载：https://www.google.com/chrome/

```bash
pip install -r requirements.txt
playwright install chromium

# 可选：以可编辑模式安装，获得 rpa 命令行入口
pip install -e .
```

**macOS 桌面自动化**（操作飞书、钉钉等原生应用）需额外安装：

```bash
# pyautogui 需要 Homebrew Python 3.11+（系统自带的 Python 3.9 不支持）
brew install python@3.12
/opt/homebrew/bin/python3.12 -m pip install pyautogui --break-system-packages
```

同时在「系统设置 → 隐私与安全性 → 屏幕录制」中授权终端。

### 2. 配置

复制 `config.yaml` 并填写，或设置环境变量：

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. 启动 Chrome（复用已登录状态）

运行启动脚本，**首次需要在浏览器中登录各目标系统，之后免登录**：

```bash
# macOS
sh tools/start_chrome.sh

# Windows
tools\start_chrome.bat
```

脚本使用独立 profile（`~/.chrome-rpa-profile`），不影响日常 Chrome 的登录状态，可两个 Chrome 窗口同时开。

### 4. 运行 Skill

```bash
# 查看所有可用 Skill
python run.py

# 运行 showcase 示例
python run.py showcase/office/excel_toolkit/excel_toolkit -- --read data.xlsx

# 运行自建 Skill
python run.py skills/my_skill
```

### 5. 定时运行 Skill

**macOS / Linux**（crontab）：

```bash
# 用法：sh tools/cron_helper.sh <skill路径> <cron表达式>
sh tools/cron_helper.sh skills/my_skill "0 9 * * 1-5"
```

脚本会打印完整的 crontab 行（含 PYTHONPATH、python 路径、日志重定向），复制后执行 `crontab -e` 粘贴即可。

**Windows**（任务计划程序）：

```powershell
# 每个工作日 09:00 运行
powershell -File tools\cron_helper.ps1 skills/my_skill 09:00 -Weekdays

# 每 30 分钟运行一次
powershell -File tools\cron_helper.ps1 skills/my_skill -EveryMinutes 30
```

脚本会打印完整的 `schtasks /Create` 命令，在管理员 PowerShell 中执行即可。

### 6. 生成新 Skill（无需写代码）

```bash
python tools/generate_skill.py
```

打开目标页面 → 描述操作 → AI 生成代码 → 保存运行。

### 7. Harness Agent（探索 → 固化为 Skill）

Harness 是**探索工具，不是生产执行器**。用它快速验证"这件事能自动化吗、需要哪几步"，确认后固化成普通 Skill 定时跑。固化后 Harness 就退场了，后续执行零 AI 成本。

**固化路径：**

```bash
# 第一步：看 LLM 怎么拆解，确认方向
python run.py harness/agent -- --goal "提取这个网页里的表格数据" --dry-run

# 第二步：提供 SOP 文档，执行后自动截图验证结果是否符合预期
python run.py harness/agent -- --goal "提取这个网页里的表格数据" --sop sops/my_task/extract.md

# 第三步：导出骨架脚本（自动生成，含步骤结构和 TODO）
python run.py harness/agent -- --goal "提取这个网页里的表格数据" --export skills/my_task_daily.py

# 第四步：打开 skills/my_task_daily.py，把 TODO 替换成确定性 Playwright 代码
# 第五步：验证
python run.py skills/my_task_daily

# 第六步：加定时任务，之后不再需要 Harness
sh tools/cron_helper.sh skills/my_task_daily "0 9 * * 1-5"
```

| | Harness（探索） | 普通 Skill（生产） |
|---|---|---|
| 步骤来源 | LLM 实时规划 | 代码写死 |
| 执行方式 | agentic loop，每步推理 | 确定性脚本 |
| AI 成本 | 每次执行都有 | 零 |
| 适合 | 第一次跑通、验证可行性 | 固化后定时执行 |

**扩展 Harness 覆盖的技能：** 在 `harness/agent.py` 的 `SKILL_REGISTRY` 中加一项，指定 `type`（browser/desktop）、`description`（给规划 LLM）、`hint`（给执行 subagent 的技术上下文）。

---

## 开发新 Skill

在 `skills/` 下新建 `.py` 文件，实现 `main()` 函数：

```python
from core.browser import open_page
from core.logger import SkillLogger
from core.config import get

async def main():
    log = SkillLogger("my_skill")

    async with open_page(get("systems.crm.url")) as page:
        log.step("打开 CRM")
        await page.click("text=导出")
        log.step("点击导出")

    log.finish()
```

### 何时引入 LLM

| 场景 | 方案 |
|---|---|
| 固定流程，页面稳定 | 纯 Playwright，不用 LLM |
| 选择器失效，UI 变了 | `vision.find_element()` → `llm.find_element()` |
| 生成个性化消息文案 | `llm.generate()` |
| 条件判断、状态识别 | `llm.decide(screenshot)` |

---

## MCP Server — 对话驱动自动化

MCP Server 是本框架的对话入口，让用户无需写代码，通过与 Claude 对话即可驱动自动化、探索新场景。

### 接入 Claude Desktop

编辑 `~/.claude/claude_desktop_config.json`（没有则新建）：

```json
{
  "mcpServers": {
    "rpa-everything": {
      "command": "python",
      "args": ["/absolute/path/to/rpa-everything/mcp_server.py"]
    }
  }
}
```

重启 Claude Desktop，左侧工具栏出现 `rpa-everything` 即表示接入成功。

### 可用工具（16 个）

浏览器和桌面工具与 agentic loop 共享同一份定义（`core/tools.py`），不会漂移。

**浏览器**

| 工具 | 说明 |
|---|---|
| `browser_navigate` | 打开指定 URL |
| `browser_screenshot` | 截取当前页面截图 |
| `browser_click` | 点击页面元素（文字 / CSS 选择器） |
| `browser_type` | 在输入框中输入文字 |
| `browser_extract_text` | 提取页面文本 |
| `browser_extract_table` | 提取页面表格（返回 JSON） |
| `browser_evaluate` | 在页面中执行 JavaScript |

**桌面**

| 工具 | 说明 |
|---|---|
| `desktop_screenshot` | 截取全屏（适用于桌面应用） |
| `desktop_click` | 点击屏幕坐标（逻辑像素，Retina 自动适配） |
| `desktop_type` | 输入文字（中文自动走剪贴板粘贴） |
| `desktop_hotkey` | 发送快捷键，如 `command+v`、`ctrl+c` |
| `desktop_find_click` | 截图 → LLM 视觉识别 → 点击 |

**Skill 管理**

| 工具 | 说明 |
|---|---|
| `skill_list` | 列出所有可用 Skill |
| `skill_run` | 运行已保存的 Skill |
| `skill_save` | 将对话生成的代码保存为 Skill |

**Harness**

| 工具 | 说明 |
|---|---|
| `orchestrate` | 接受自然语言目标，自动规划并执行多个 Skill；支持 `dry_run`（只规划）、`export`（导出骨架脚本）、`sop`（执行后截图验证） |

### 典型使用流程

**探索新场景：**
1. 打开 Claude Desktop，选择 `rpa-everything` 工具
2. 描述目标：「帮我查一下 CRM 里今天到期的跟进记录」
3. Claude 自动截图、操作页面、返回结果
4. 确认无误：「把这个操作保存成 Skill」→ 代码保存到 `skills/`

**操作桌面应用（飞书示例）：**
```
你: 帮我在飞书某个群里发一条消息，内容是「今天的进度更新……」
Claude: desktop_screenshot → 识别输入框位置 → desktop_click → desktop_type → 截图确认
```

### 安全边界

MCP Server 把「操作屏幕、写入并运行代码」的能力交给了 LLM，这意味着**模型读到的任何内容（包括网页正文）都可能间接影响它调用工具的方式**（prompt injection）。使用时请注意：

- 探索阶段让 Claude 操作**不可信网页**时，留意它发起的 `skill_save` / `skill_run` 调用是否符合你的意图，Claude Desktop 的工具确认弹窗不要盲目放行
- `skill_save` 只允许写入 `skills/` 目录内；保存的代码在运行前建议先人工过一眼
- 固化后的 Skill 是纯脚本、不接触 LLM，不存在此类风险——这也是本框架主张「探索归探索、生产归生产」的原因之一

---

## Showcase 状态

| Skill | 路线 | 状态 | 备注 |
|---|---|---|---|
| `showcase/web/extract_table` | Browser DOM | ✅ 可运行 | `--url https://www.w3schools.com/html/html_tables.asp` |
| `showcase/web/click_by_vision` | Browser + LLM Vision | ✅ 可运行 | config.yaml 中 `model: global.anthropic.claude-sonnet-4-6` |
| `showcase/app/template_click` | Desktop 图像模板匹配 | ✅ 可运行 | 零 AI 成本；`--template assets/<系统>/<按钮>.png`（模板自己截） |
| `showcase/office/excel_toolkit` | 文件格式操作（openpyxl） | ✅ 可运行 | 零 AI 成本，可跑服务器；`--read data.xlsx` |
| `showcase/office/ppt_generator` | 文件格式操作（python-pptx） | ✅ 可运行 | 零 AI 成本，可跑服务器；`--output out.pptx --data '[...]'` |
| `showcase/office/word_report` | 文件格式操作（python-docx） | ✅ 可运行 | 零 AI 成本，可跑服务器；`--output out.docx --title "标题" --data '[...]'` |
| `skills/feishu_project_daily` | Browser API 拦截 | ✅ 可运行 | 需 Chrome 已登录飞书项目，每日定时触发 |

> 运行 Browser 类 Skill 前：确认 `sh tools/start_chrome.sh` 已启动 RPA Chrome（不是飞书桌面端的 Electron）。

---

## 常见问题

**Q: `Chrome 未以调试端口启动` 错误**
先运行 `sh tools/start_chrome.sh`，确认终端输出 `✅ Chrome 已就绪`。飞书桌面端也会占用 9222 端口，两者冲突时先关闭飞书再启动 RPA Chrome。

**Q: `Browser context management is not supported`**
9222 端口被飞书 Electron 抢占。运行 `lsof -i :9222 | grep LISTEN` 确认是哪个进程，再重启 RPA Chrome。

**Q: click_by_vision 报视觉模型错误**
config.yaml 中 `model` 需改为多模态模型。内网 AI 网关示例：`global.anthropic.claude-sonnet-4-6`；直连 Anthropic：`claude-sonnet-4-6`。

**Q: 桌面类 Skill 找不到元素（换了机器/目标应用改版）**
桌面类 Skill 用图像模板匹配定位元素（`assets/<系统名>/*.png`），不是硬编码坐标。换机器、分辨率不同、目标应用改版都可能导致模板匹配失败，需要重新截图替换对应模板文件，参考 [ARCHITECTURE.md](ARCHITECTURE.md) 的坐标系陷阱说明。

---

## 参与开发

```bash
pip install -r requirements-dev.txt   # 含 pytest / ruff
ruff check .                          # lint
pytest                                # 测试（browser 用例无 Chrome 时自动 skip）
```

CI 会在每个 PR 上自动跑 lint + 测试。

`showcase/` 下的 Skill 是通用示例，**主要价值是提供结构参考**——照着把系统地址、字段、模板图换成自己的系统即可。贡献新 Skill 请参考 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 平台支持

| 平台 | 状态 |
|---|---|
| macOS | ✅ 支持（Web + API + 桌面控制，需 Homebrew Python 3.12 + 屏幕录制权限）|
| Windows | ✅ 主要支持（含 pywinauto 原生窗口控制，定时任务用 cron_helper.ps1）|
| HarmonyOS PC | ⏳ 待评估 |

---

## License

[MIT](LICENSE)
