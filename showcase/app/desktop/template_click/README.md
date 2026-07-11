# template_click — 图像模板匹配点击

桌面自动化路线（PyAutoGUI + 图像模板匹配）的最小可运行示例。
给一张目标元素的截图，在当前屏幕上定位并点击它——零 AI 成本、确定性、抗小幅缩放漂移。

## 用法

```bash
# 1. 截一张目标按钮/图标的图，存到 assets/<系统名>/
# 2. 运行：
python run.py showcase/app/desktop/template_click/template_click -- --template assets/feishu/approve_btn.png

# 可选参数
#   --app "飞书"        先把应用切到前台
#   --double            双击
#   --confidence 0.8    降低匹配阈值（模板略有差异时）
#   --timeout 10        延长查找时间
```

## 模板截图要点

- 贴着元素边缘截，少带背景（背景变化会拉低置信度）
- 在**将要运行脚本的那台机器**上截（分辨率/缩放不同会导致匹配失败，
  `locate_and_click` 内置多尺度匹配可容忍常见 DPI 差异，但同机截图最稳）
- 换机器或目标应用改版后重新截图即可，不用改代码

## 何时用这条路线

| 情况 | 建议 |
|---|---|
| 按钮/图标样式固定 | ✅ 模板匹配（本示例） |
| 元素内容每次都变（如验证码、动态列表项） | 退到 `core.llm.find_element()` 视觉识别 |
| 应用是 Electron（飞书/钉钉桌面版） | 优先试 Playwright 连调试端口（`core/browser.py`），DOM 比像素稳 |
