# app/ — 桌面应用类 Skill

放操作原生桌面应用（Electron / 原生窗口，无 Web 接口可用）的 Skill。

**默认技术路线：图像模板匹配**，不是截图发给 LLM 猜坐标——把目标按钮/图标截一次图存成模板
（放在 `assets/<系统名>/*.png`），用 `core.desktop.locate_and_click()` 精确定位，零 AI 成本、
确定性强。详见 [ARCHITECTURE.md](../../ARCHITECTURE.md) 的"元素定位降级链"一节。

只有目标元素内容每次运行都变、没法预先截模板时，才退到 `core.llm.find_element()`（LLM 视觉识别）。

内置示例：[template_click](template_click/) —— 模板路径由参数传入（机器无关），
截一张自己系统上的按钮图就能跑，照着它写自己的桌面 Skill 即可。

注意模板图片本身跟机器强相关（分辨率/缩放），所以 `assets/` 下的模板需要自己截，
不要复用别人的。参考 `core/desktop.py` 的 `locate_and_click()` / `activate_app()` /
`physical_to_logical()`，或参考 [CONTRIBUTING.md](../../CONTRIBUTING.md) 贡献通用示例。
