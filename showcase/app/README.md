# app/ — 桌面应用类 Skill

放操作原生桌面应用（Electron / 原生窗口，无 Web 接口可用）的 Skill。

**默认技术路线：图像模板匹配**，不是截图发给 LLM 猜坐标——把目标按钮/图标截一次图存成模板
（放在 `assets/<系统名>/*.png`），用 `core.desktop.locate_and_click()` 精确定位，零 AI 成本、
确定性强。详见 [ARCHITECTURE.md](../../ARCHITECTURE.md) 的"元素定位降级链"一节。

只有目标元素内容每次运行都变、没法预先截模板时，才退到 `core.llm.find_element()`（LLM 视觉识别）。

当前目录暂无内置示例——桌面应用截图/坐标跟每个人的系统和分辨率强相关，不适合直接复用别人截的模板。
参考 `core/desktop.py` 的 `locate_and_click()` / `activate_app()` / `physical_to_logical()`
自己写一个，或参考 [CONTRIBUTING.md](../../CONTRIBUTING.md) 贡献一个通用示例回来。
