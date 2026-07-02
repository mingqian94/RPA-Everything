# 架构设计

## 设计原则

**AI 是兜底，不是主路。**

自动化脚本的稳定性和 AI 调用成本是矛盾的。本框架的解决方式是分阶段：

- **探索阶段**：AI 在线，帮用户搞清楚怎么操作、生成脚本
- **执行阶段**：脚本离线跑，只有 UI 变化或需要生成内容时才调 AI

流程固化后，一次任务的 AI 成本趋近于零。

---

## 分层结构

```
┌─────────────────────────────────────────┐
│              入口层                      │
│  MCP Server（对话驱动）  run.py（脚本）  │
├─────────────────────────────────────────┤
│              Skill 层                   │
│  showcase/（示例）  skills/（用户自建）    │
│  每个 Skill = 一个业务流程的完整实现     │
├────────────────┬────────────────────────┤
│   core/        │   connectors/          │
│   通用能力      │   系统连接器           │
│   browser.py   │   feishu.py            │
│   desktop.py   │   http.py              │
│   llm.py       │                        │
│   vision.py    │                        │
└────────────────┴────────────────────────┘
```

### 各层职责

**入口层**
- `mcp_server.py`：Claude Desktop 对话入口，将框架能力封装为 MCP 工具
- `run.py`：命令行入口，直接执行已有 Skill，无 AI 参与

**Skill 层**
- 每个 Skill 是一个 `.py` 文件，实现 `main()` 函数
- 只写业务逻辑，不关心底层平台差异
- `showcase/` 是官方示例，`skills/` 是用户本地自建，互不干扰

**core/ — 通用能力**
- `browser.py`：Playwright 封装，复用已登录 Chrome（CDP 连接）
- `desktop.py`：桌面自动化，屏蔽 macOS / Windows 差异
- `llm.py`：Claude API 封装，提供 generate / decide / find_element 三类接口
- `config.py`：统一读取 config.yaml 和环境变量
- `logger.py`：结构化执行日志，每次 Skill 运行保存到 `logs/`

**connectors/ — 系统连接**
- 封装第三方系统的认证和 API 调用
- Skill 直接引用，不关心 token 刷新细节

---

## 技术路线选择

写一个新 Skill 时，第一个决策是用哪种自动化方式。选错了，稳定性和维护成本会差一个数量级。

### 决策树

```
目标系统有公开 API？
├── 是 → 【API / Script】直接调接口，不碰 UI
│         例：飞书 API 调用（connectors/feishu.py）
│
└── 否 → 目标是 Excel / PPT / Word 文件？
    ├── 是 → 【文件格式操作】openpyxl / python-pptx / python-docx，不打开对应应用
    │         例：showcase/office/*，可跑服务器，跟 API 同一档可靠性
    │
    └── 否 → 目标是 Web 应用？
        ├── 是 → DOM 可读、选择器稳定？
        │        ├── 是 → 【Browser 自动化】Playwright + CSS/text 选择器
        │        │         例：网页表格提取、CRM/HR 系统查询
        │        │
        │        └── 否（选择器混淆/频繁变动）→ 【Browser + LLM Vision】
        │                  截图发给 LLM，描述元素位置，再点坐标
        │
        └── 否 → 桌面应用（Electron / 原生）
                 ├── Windows → 【pywinauto UI Automation】读原生控件树
                 └── macOS  → UI 元素样式固定（按钮/图标）？
                              ├── 是 → 【图像模板匹配】locate_and_click()
                              │         例：飞书圈子发帖、飞书审批批量同意
                              └── 否 → 【Visual Model】截图 + LLM find_element
                                        仅用于内容随每次运行变化、无法预先截模板的元素
```

### 六种路线的取舍

| 方式 | 稳定性 | 速度 | AI 成本 | 适用场景 |
|---|---|---|---|---|
| API / Script | ⭐⭐⭐⭐⭐ | 极快 | 零 | 有 API 的系统 |
| 文件格式操作（Office） | ⭐⭐⭐⭐⭐ | 极快 | 零 | Excel/PPT/Word，跟 API 同一档，不需要对应应用打开 |
| Browser 自动化 | ⭐⭐⭐⭐ | 快 | 零（执行时） | Web 系统，DOM 可读 |
| 图像模板匹配（桌面） | ⭐⭐⭐⭐ | 快 | 零（执行时） | 桌面应用，目标元素样式固定（按钮、图标、导航项） |
| Browser + LLM Vision | ⭐⭐⭐ | 中 | 低（每步截图） | Web 系统，选择器不稳定 |
| Visual Model（桌面） | ⭐⭐ | 慢 | 中（每步截图），且坐标判断精度有限 | 桌面应用，元素内容随每次运行变化，无法预先截模板 |

**稳定性差异的根本原因：**
- API：系统主动维护兼容性，变更有文档
- 文件格式操作：`.xlsx`/`.pptx`/`.docx` 本质是标准化的 XML 压缩包，格式本身很稳定，不依赖任何应用是否安装、是否打开
- Browser DOM：选择器随前端迭代而变，但变化频率可预期
- 图像模板匹配：只要目标元素的视觉样式不变（哪怕内容周围的其他区域在变），匹配就稳定；换机器/换分辨率需要重新截模板，但比坐标标定更抗小幅漂移（`locate_and_click` 内置多尺度容错）
- 视觉模型：依赖截图和 LLM 的理解能力，窗口位置、分辨率、UI 皮肤变化都可能失效——更关键的是，LLM 从截图读出的坐标和实际点击坐标可能不在同一套坐标系里（比如 macOS Retina 屏幕物理像素 vs 逻辑像素相差 2 倍），这类问题比"选择器失效"更隐蔽，容易表现成诡异的误点击而不是直接报错

### 反常识：不要默认选视觉模型（桌面场景默认选模板匹配，不是视觉模型）

视觉模型看起来"最像人"，但它是最后手段，不是第一选择。每次定位元素都要调 LLM，慢、贵、不稳定，而且"不稳定"不只是偶尔找不到元素——坐标系搞错会导致**看起来点中了，实际点到别的地方**，比找不到元素更难排查。

**桌面场景的默认选择是图像模板匹配，不是视觉模型**——按钮、图标、导航项这类样式固定的 UI 元素，截一次图存成模板（`assets/<系统名>/*.png`），用 `core.desktop.locate_and_click()` 精确定位，不需要 LLM 参与。

**什么时候才用视觉模型：**
1. 目标元素内容每次运行都不一样，没法预先截模板（比如根据文字内容定位某一条具体记录）
2. 探索阶段，快速验证流程可行性，尚未决定要不要固化成模板

### 实际案例对照

| Skill | 路线 | 选择理由 |
|---|---|---|
| `web/extract_table` | Browser 自动化 | 通用场景；`<table>` 是标准 HTML，不依赖 class |
| `office/excel_toolkit`、`ppt_generator`、`word_report` | 文件格式操作 | 目标本身就是文件，不是要操作一个"应用"；直接读写 `.xlsx`/`.pptx`/`.docx` 结构，没有 UI 这一层 |

桌面类 Skill（图像模板匹配路线）没有内置示例——模板图跟每个人的系统和分辨率强相关，参考
`showcase/app/README.md` 自己写一个。

---

## 元素定位降级链

UI 自动化最大的不稳定来源是"找不到元素"。浏览器类和桌面类的降级链不一样：

**浏览器类：**
```
1. CSS/XPath 选择器      → 毫秒级，零成本，优先
2. Claude Vision         → 按 token 计费，多模态模型（sonnet 以上）
3. 人工确认              → 最终兜底，触发通知等待人介入
```

**桌面类：**
```
1. 图像模板匹配          → 零成本、确定性，core.desktop.locate_and_click()
2. Claude Vision         → 按 token 计费，且坐标判断精度不如模板匹配
3. 人工确认              → 最终兜底，触发通知等待人介入
```

浏览器类 Skill 代码通常只写第 1 层；`llm.find_element()` 实现第 2 层。桌面类 Skill 默认走模板匹配这一层；只有目标元素内容每次运行都变、没法预先截模板时才退到 Claude Vision。

---

## MCP Server 工具设计

工具按操作对象分组，而不是按功能分组，方便 Claude 在对话中选择：

- `browser_*`：操作浏览器（Web / Electron 应用）
- `desktop_*`：操作桌面（截图、点击、键盘输入）
- `skill_*`：Skill 管理（列表、运行、保存）
- `orchestrate`：Harness 入口，接受自然语言目标，规划并执行多个 Skill

**关键设计：`skill_save`**

对话探索完成后，用户说"保存这个操作"，`skill_save` 把当前对话生成的代码写入 `skills/`，下次直接 `run.py` 执行，不再经过 MCP。这是"探索 → 固化"闭环的关键节点。

---

## desktop.py 的平台适配

macOS 和 Windows 在桌面自动化上差异较大，`desktop.py` 统一封装：

| 能力 | macOS | Windows |
|---|---|---|
| 截图 | `screencapture -x`（无需辅助功能权限） | pyautogui |
| 鼠标/键盘 | pyautogui（需 Homebrew Python 3.11+） | pyautogui |
| 元素定位 | 图像模板匹配 `locate_and_click()`，跨平台同一套代码 | 同 macOS；结构化元素还可用 `win_find_element()`（pywinauto） |
| 中文输入 | `pbcopy` + `Cmd+V` 粘贴（绕过 IME） | `pyperclip` + `Ctrl+V` |
| 激活窗口 | `osascript tell application "System Events" ...`（按进程名寻址，比 `tell application X to activate` 更可靠） | pygetwindow |
| 原生控件访问 | 不支持 | pywinauto UI Automation |

**为什么 macOS 桌面自动化要用 Homebrew Python？**
系统自带 Python 3.9 对应的 `pyobjc-core` 包已被 yanked，安装会失败。Homebrew Python 3.11+ 是目前最稳定的路径，推荐 3.12。

**Retina 屏幕的坐标系陷阱：** `screenshot()` 在 Retina Mac 上返回物理像素尺寸（如 2880×1800），但 `click()`/`move_to()` 用的是 pyautogui 的逻辑像素坐标系（如 1440×900）。如果坐标是从截图直接读出来再传给点击函数，会偏移整整一个缩放倍数（这台机器是 2x）——`core/desktop.py` 的 `physical_to_logical()` 处理这层换算，已经接入 `core/tools.py`（Harness 用）和 `mcp_server.py`（Claude Desktop 直连用）两条工具调用路径。`locate_and_click()` 内部也走这层换算，调用方不需要关心。如果以后哪个 Skill 里还留着手工标定的坐标常量（约定含义是"预标定的逻辑像素"），要注意它和 `physical_to_logical()` 的输入（物理像素）不是同一套坐标系，别搞混。

---

## 部署模式

框架支持两种运行环境，取决于 Skill 的类型：

**服务器部署（API 类 Skill）**

```
cron / 调度系统
    ↓
python run.py skills/send_notification
    ↓
connectors/feishu.py → 飞书 API
```

纯 HTTP 调用，无界面依赖，适合定时无人值守任务。

**本地部署（界面类 Skill）**

```
用户触发 / 本地 cron
    ↓
python run.py skills/post_hetaoquan
    ↓
core/desktop.py → 飞书桌面应用（需前台窗口）
core/browser.py → Chrome（需已登录会话）
```

需要物理屏幕，适合一台常开的专用机（Mac Mini / Windows 主机）。

**混合场景建议**：把流程拆开——界面操作本地跑，结果通过 API 发出去，两段分别部署。

---

## Agent 架构

Harness 使用 **Plan-and-Execute** 模式，Planner 和 Worker 职责完全分离。

```
用户目标（自然语言）
        │
        ▼
┌───────────────────┐
│     Planner       │  harness/agent.py  plan()
│  单次 LLM 调用    │  输出 JSON 任务序列，不执行
│  输出任务序列     │  失败自动重试一次
└────────┬──────────┘
         │  tasks: [{skill, goal, label, parallel}, ...]
         ▼
┌───────────────────────────────────────┐
│           Executor                    │  harness/agent.py  _execute_plan()
│  串行执行；parallel=true 的相邻任务   │  结构化日志记录每步结果
│  用 asyncio.gather 并发              │
└──────┬──────────────────┬────────────┘
       │                  │
       ▼                  ▼
┌────────────┐    ┌────────────┐
│  Worker A  │    │  Worker B  │  core/agent.py  run_browser / run_desktop
│ ReAct Loop │    │ ReAct Loop │  每个 Worker 独立循环，最多 30 步
│ 最多 2 次  │    │ 最多 2 次  │  失败后带错误上下文重试一次
│ 尝试       │    │ 尝试       │
└────────────┘    └────────────┘
```

### 为什么这样分层

**Planner 和 Worker 解耦的好处：**
- Planner 只看"做什么"，不关心浏览器状态、坐标、选择器
- Worker 只看"怎么做"，有完整的工具集和重试能力
- 两层可以独立升级：换更强的 Planner 不影响 Worker，Worker 加新工具不影响规划逻辑

**Worker 用 ReAct 而不是固定脚本的原因：**
- 每个子任务的中间状态不可预测（页面加载时间、弹窗、登录跳转）
- ReAct 让 Worker 自己处理这些意外，Planner 只需给出目标

### 和其他 Agent 模式的对比

| 模式 | 特点 | 本框架 |
|---|---|---|
| 纯 ReAct | 单 Agent 循环，边做边想 | Worker 内部是 ReAct |
| Plan-and-Execute | 先规划后执行，两层解耦 | ✅ 整体架构 |
| Multi-Agent（共享记忆） | Agent 间动态传递中间结果 | ❌ Worker 互相隔离 |
| Reflexion | 执行后反思，修改计划重跑 | ❌ 未实现 |

Worker 之间目前完全隔离——每个 Worker 只拿到自己的 `goal` 字符串，不知道其他 Worker 的结果。这对独立子任务够用，但如果后续任务需要依赖前序任务的输出，需要在 Planner 的规划阶段就把结果传递路径写进 `goal` 字段里。

### 重试机制

```
plan() ──JSON 解析失败──► 重试 1 次 ──再失败──► 抛 ValueError

_run_task() ──subagent 返回 error──► 把错误原因追加到 goal，重试 1 次
                                   ──再失败──► 记录日志，继续执行下一任务
```

---

## 已知局限

1. **无执行隔离**：Skill 直接操作用户桌面，出错没有撤销。目前靠"截图确认再执行"缓解，高频批量场景需要额外防护（比如循环处理一批待办时，加一个"处理完的数量不再减少就终止"的安全阀，避免卡住后无限循环误点）。
2. **模板脆弱性**：图像模板匹配依赖目标元素的视觉样式不变，换机器、换分辨率、系统主题变化（如深色模式）、目标应用改版都可能导致匹配失败，需要重新截模板。`locate_and_click()` 内置多尺度容错，能扛住小幅缩放漂移，但换根本样式仍需人工重截。`desktop_find_click`（LLM 视觉识别）可以作为完全没有模板时的兜底，但不要指望它替代模板匹配的可靠性——这正是这次踩过的坑：LLM 判断坐标本身就不够准，Retina 屏幕物理/逻辑像素不一致更是直接导致过误点击其他应用。
3. **Chrome CDP 依赖**：浏览器自动化要求 Chrome 以调试端口启动并保持登录状态，进程重启后需要重新登录。
