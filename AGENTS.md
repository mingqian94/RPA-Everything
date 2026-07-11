# Agent Integration Guide

本文件供 AI Agent 读取，用于自主判断如何接入本框架的自动化能力。

---

## 框架能力概览

本框架提供两类能力：

1. **探索模式**：Agent 实时调用工具，截图、操作浏览器/桌面、探索新的自动化场景
2. **执行模式**：调用已固化的 Skill 脚本，无需 AI 参与，确定性执行

---

## 接入路径选择

### 路径一：MCP Server（推荐，支持探索模式）

如果你支持 MCP（Model Context Protocol），直接连接本框架的 MCP Server。

**启动服务：**

```bash
python /path/to/rpa-everything/mcp_server.py
```

**配置示例（Claude Desktop 格式）：**

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

**连接后可用工具（34 个）：**

| 工具 | 说明 |
|---|---|
| `browser_navigate` | 打开 URL |
| `browser_screenshot` | 截取当前页面 |
| `browser_click` | 点击元素（文字 / CSS 选择器） |
| `browser_type` | 在输入框输入文字 |
| `browser_extract_text` | 提取页面文本 |
| `browser_extract_table` | 提取页面表格（返回 JSON） |
| `desktop_screenshot` | 截取全屏 |
| `desktop_click` | 点击屏幕坐标 |
| `desktop_type` | 输入文字（中文自动走剪贴板） |
| `desktop_hotkey` | 发送快捷键 |
| `desktop_find_click` | 截图 → LLM 视觉识别 → 点击 |
| `android_devices` | 列出 ADB 设备 |
| `android_screenshot` | 截取 Android 设备屏幕 |
| `android_tap` | 按像素坐标或屏幕比例点击 |
| `android_dump_ui` | 导出 UIAutomator 节点 JSON |
| `android_tap_element` | 按文字 / resource-id / content-desc 点击元素 |
| `android_swipe` | 按像素坐标或屏幕比例滑动 |
| `android_key` | 发送 Android keyevent |
| `android_type` | 输入文字；`unicode=true` 使用 ADBKeyboard |
| `android_push_file` | 推送文件到设备，可选触发媒体扫描 |
| `android_diagnostics` | 检查 ADB、设备状态、分辨率和截图权限 |
| `ios_devices` | 列出 pymobiledevice3 可识别的 iPhone |
| `ios_diagnostics` | 检查 iPhone 半自动前置条件 |
| `ios_copy_text` | 复制文本到 iPhone 剪贴板 |
| `ios_launch_app` | 按 bundle id 打开 iPhone App |
| `ios_screenshot` | 截取 iPhone 屏幕留证 |
| `skill_list` | 列出所有可用 Skill |
| `skill_run` | 运行已保存的 Skill |
| `skill_save` | 将代码保存为新 Skill |
| `orchestrate` | 接受自然语言目标，Harness 自动规划并执行；支持 `dry_run`、`export` 导出骨架脚本、`export_trace` 导出真实工具调用初稿脚本、`sop` 执行后截图验证 |
| `skill_solidify` | 将 trace JSON 固化为可监督首跑的 Skill，并给出语法检查和风险 review 清单 |
| `run_list` | 查询最近 Skill 运行记录或单次运行详情 |
| `runtime_snapshot` | 只读查询本机 Harness 环境、可用 Skill/能力、安全边界和下一步建议 |

---

### 路径二：CLI 直接调用（支持执行模式 + 有限探索）

如果你可以执行 shell 命令，通过命令行使用框架。

**执行固化 Skill：**

```bash
# 小白首次安装 / 体检
powershell -ExecutionPolicy Bypass -File tools\setup.ps1  # Windows
sh tools/setup.sh                                         # macOS / Linux
python run.py harness/doctor
python run.py harness/runtime --json

python run.py showcase/web/extract_table -- --url https://example.com
python run.py showcase/web/xhs/search_posts -- --keyword "露营" --output data/xhs_search.json
python run.py showcase/web/xhs/post_detail -- --url https://www.xiaohongshu.com/explore/xxx
python run.py showcase/app/post_circle/post_circle -- --text "内容"
python run.py showcase/android/xhs_note/xhs_note -- --profile data/xhs_profile.json --dry-run
python run.py showcase/ios/iphone_assist/iphone_assist -- --copy-text "内容" --launch-wechat
python run.py skills/my_skill
```

**Harness Agent（自然语言目标 → 自动规划执行）：**

```bash
# 只看规划，不执行
python run.py harness/agent -- --goal "帮我查今天的 OJ 排行榜" --dry-run

# 完整执行
python run.py harness/agent -- --goal "帮我查今天的 OJ 排行榜"

# 执行后导出为可复用的 Skill 骨架
python run.py harness/agent -- --goal "..." --export skills/my_new_skill.py

# 执行一次后导出真实工具调用轨迹，作为可 review 的初稿 Skill
python run.py harness/agent -- --goal "..." --export-trace skills/my_new_skill.py

# 执行一次后导出可 replay 的 JSON trace
python run.py harness/agent -- --goal "..." --trace-json data/outputs/trace.json

# dry-run 回放 trace，确认会执行哪些工具调用
python run.py harness/replay -- --trace data/outputs/trace.json --dry-run

# 将轨迹固化为可监督首跑的 Skill；先查看 manifest，再决定是否定时运行
python run.py harness/solidify -- --trace data/outputs/trace.json --output skills/my_new_skill.py

# 查看最近任务运行；Agent 也可以通过 run_list 查询
python run.py harness/runs -- --limit 20

# 运行 Harness 静态评估集
python evals/run.py

# Android 真机 smoke test（默认不注入输入）
python run.py showcase/android/smoke_test/smoke_test -- --output data/outputs/android_smoke.json

# 提供 SOP 文档，执行后截图验证结果是否符合规范
python run.py harness/agent -- --goal "..." --sop sops/feishu/post_circle.md

# 允许执行发布/审批/发送等真实外部副作用任务时，必须显式确认
python run.py harness/agent -- --goal "..." --confirm-external

# 登录/MFA 需要人工时，返回结构化 needs_human_step，而不是等待终端输入
python run.py harness/agent -- --goal "..." --handoff-on-login
```

**列出所有可用 Skill：**

```bash
python run.py
```

---

## 安全策略

完整策略见 `SECURITY.md`。默认原则：

- 探索模式会让 LLM 操作浏览器、桌面或 Android，必须警惕网页/应用内容里的 Prompt Injection。
- 发布、发送、审批、付款、删除、修改远端数据等真实外部副作用必须显式使用 `--confirm-external`。
- 密钥、账号、客户数据、Cookie、Token、私有 URL 不得写入 Skill、测试、文档或截图。
- Secret 引用使用 `${secret:name}`，并在本机环境变量中设置 `RPA_SECRET_NAME`；日志和 trace 会对常见密钥、Token、手机号和邮箱脱敏。
- 分享 `logs/`、`data/outputs/` 前先检查是否包含页面文本、URL、截图或个人数据。

---

## 前置条件

在调用任何工具前，确认以下条件满足：

| 条件 | 检查方式 |
|---|---|
| Chrome 以调试端口启动 | `curl -s http://localhost:9222/json` 有返回 |
| Python 依赖已安装 | `pip install -r requirements.txt` |
| config.yaml 已配置 | 至少填写 `llm.api_key` |
| 新用户环境体检 | `python run.py harness/doctor` |
| Android ADB 已配置（Android 手机类任务） | `python run.py showcase/android/adb_basics/adb_basics -- --devices` |
| iPhone 半自动依赖已配置（iPhone 任务） | `pip install pymobiledevice3` 后运行 `python run.py showcase/ios/iphone_assist/iphone_assist -- --devices` |
| macOS 屏幕录制权限 | 系统设置 → 隐私与安全性 → 屏幕录制 → 授权终端 |

**启动 Chrome（浏览器类工具的前提）：**

```bash
sh tools/start_chrome.sh   # macOS
tools\start_chrome.bat     # Windows
```

---

## 判断建议

- 支持 MCP → 选路径一，可完整使用探索 + 执行全部能力；iPhone 当前是半自动准备/留证，不是远程触控
- 只能执行 shell 命令 → 选路径二，执行固化 Skill 或通过 Harness 完成有限探索
- 两者都支持 → 路径一优先，路径二作为补充
