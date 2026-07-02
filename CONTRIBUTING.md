# Contributing

欢迎贡献 Skill、修复 Bug、或改进框架核心能力。

## 贡献类型

### 1. 提交 SOP 文档到 sops/

最低门槛的贡献方式：用自然语言写清楚"怎么做"，框架用它执行并自动验证结果。

**放哪里：** `sops/<系统或业务>/<任务名>.md`

**写什么：**
```markdown
# 发飞书圈子帖子

## 前置条件
- 飞书桌面端已登录

## 操作步骤
1. 打开飞书，点击左侧导航栏「圈子」图标
2. 进入目标版块，点击「发帖」按钮
3. 填写标题和正文，选择版块分类
4. 点击「发布」

## 完成状态
帖子出现在版块 feed 顶部，显示"刚刚"时间戳。
```

**怎么测：**
```bash
python run.py harness/agent -- \
  --goal "在飞书圈子发一条测试帖" \
  --sop sops/feishu/post_circle.md
```

执行完框架自动截图，LLM 对照「完成状态」判断是否通过。**提交 PR 时附上 verify 通过的截图即可。**

---

### 2. 提交新 Skill 到 showcase/

适合场景：你在某个行业 / 系统上有可复用的自动化流程，希望分享给其他人参考。

**要求：**
- 放在对应技术类型目录下：`showcase/web/`（浏览器类）、`showcase/app/`（桌面应用类）、`showcase/office/`（Excel/PPT/Word 文件操作），例如 `showcase/web/workday/export_attendance.py`
- 实现 `main()` 函数，使用 `core/` 提供的通用能力
- 包含一个同目录的 `README.md`，说明：前置条件、参数配置、运行方式
- 敏感信息（URL、账号）放入 `config.yaml` 读取，不硬编码

**参考结构：**
```
showcase/office/excel_toolkit/
├── README.md
└── excel_toolkit.py
```

### 3. 改进 core/ 或 connectors/

适合场景：发现某个平台 / 系统的适配问题，或有更稳定的实现方式。

- `core/` 的改动要保持跨平台兼容（macOS + Windows）
- 新增 connector 参考 `connectors/feishu.py` 的结构

### 4. Bug 报告 / 功能建议

直接开 Issue，描述：
- 操作系统和 Python 版本
- 复现步骤
- 期望行为 vs 实际行为

---

## 开发环境

```bash
git clone https://github.com/mingqian94/RPA-Everything.git
cd rpa-everything
pip install -r requirements.txt
playwright install chromium
```

macOS 桌面自动化需要额外步骤，见 [README.md](README.md#1-安装依赖)。

---

## Skill 开发规范

```python
# showcase/web/your_system/your_skill.py（或 app/，桌面类；或 office/，Excel/PPT/Word 类）

from core.browser import open_page
from core.logger import SkillLogger
from core.config import get

async def main():
    log = SkillLogger("your_skill")

    # 从 config.yaml 读取配置，不硬编码
    url = get("systems.your_system.url")

    async with open_page(url) as page:
        log.step("打开页面")
        # ... 你的操作
        log.step("完成")

    log.finish()
```

**原则：**
- Skill 只写业务逻辑，底层能力全走 `core/`
- 只在必要时调 LLM（见 [README — 何时引入 LLM](README.md#何时引入-llm)）
- 每个关键步骤调一次 `log.step()`，方便定位问题

---

## 测试

### 运行方式

```bash
# 只跑纯逻辑测试（无需任何前置条件，1 秒内完成）
python3 -m pytest

# 同时跑浏览器测试（需先启动 Chrome）
sh tools/start_chrome.sh
python3 -m pytest
```

Chrome 未启动时，浏览器测试自动 skip，不会报错。

### 测试分层

| 层级 | 标记 | 覆盖范围 | 前置条件 |
|---|---|---|---|
| unit | 默认 | 配置读取、日志结构、数据解析函数 | 无 |
| browser | `@pytest.mark.browser` | Chrome CDP 连通性、extract_table 公开 URL | Chrome 已启动 |

### 覆盖范围的诚实说明

自动化测试覆盖**纯逻辑层**（config / logger / 数据解析）和**基础连通性**。

真正的自动化操作序列（点击、截图、表单填写）无法自动测试，因为它们依赖真实系统的登录状态和屏幕环境。对这类场景，手动验证是唯一可靠的方式：

```bash
# 验证规划是否合理（不实际执行）
python3 run.py harness/agent -- --goal "查询今天的 OJ 排行" --dry-run

# 验证 Skill 能跑通
python3 run.py showcase/web/extract_table -- --url https://www.w3schools.com/html/html_tables.asp
```

### 提交新 Skill 时

PR 里附上 `--dry-run` 输出或实际运行截图，证明流程在你的环境里跑通了。

---

## PR 流程

1. Fork → 新建分支（`feat/skill-name` 或 `fix/issue-description`）
2. 提交 PR，描述：这个 Skill / 修复解决什么问题、在哪个系统上验证过
3. showcase/ 下的新 Skill 需要附上截图或录屏，证明能跑通

---

感谢贡献。
