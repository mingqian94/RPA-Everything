# app/ — 应用自动化

应用按**控制通道**分两类。Harness 的选择顺序是：已注册的直连 Integration → 桌面 UI；
不要因为应用名称相同，就假设它存在 MCP 或 CLI。

## integration/ — MCP / CLI / API 直连

放能通过应用自己的 MCP Server、CLI 或 API 完成工作的 Skill。它们直接调用结构化接口，
不打开应用窗口、不截图，也不使用视觉识别。这是有可用接入时的首选路线。

当前没有随仓库分发的第三方直连示例：每个应用的安装、认证和权限都不同。接入一个具体应用时，
在 `integration/<应用名>/` 写独立 Skill，并在 README 中写明前置条件、认证变量和可执行命令；
不得把 token、Cookie 或客户数据提交到仓库。

## desktop/ — 窗口 UI 自动化

放没有可用直连能力时的 Electron / 原生窗口 Skill。优先使用 Windows UI Automation 或图像模板匹配，
而不是截图发给 LLM 猜坐标。把目标按钮/图标截一次图存为模板
（`assets/<系统名>/*.png`），用 `core.desktop.locate_and_click()` 精确定位，零 AI 成本、确定性强。
只有元素内容每次都变、无法用 UI 节点或模板定位时，才退到视觉识别。

内置示例：[desktop/template_click](desktop/template_click/) —— 模板路径由参数传入，
截一张自己系统上的按钮图就能运行。

模板图片和机器的分辨率/缩放有关，必须自己截取，不要复用别人的。参考
`core/desktop.py` 的 `locate_and_click()` / `activate_app()` / `physical_to_logical()`，
或参考 [CONTRIBUTING.md](../../CONTRIBUTING.md) 贡献通用示例。
