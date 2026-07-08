# Skill Showcase

官方精选 Skill 目录，覆盖通用 Web 操作和垂直行业场景，开箱即用。

## 通用 Web

| Skill | 说明 | 需要 LLM | 运行命令 |
|---|---|---|---|
| `web/extract_table` | 提取任意网页的 HTML 表格，返回 JSON | 否 | `python run.py showcase/web/extract_table -- --url <URL>` |
| `web/click_by_vision` | 截图发给 LLM，识别目标元素并点击 | 是（多模态模型）| `python run.py showcase/web/click_by_vision -- --url <URL> --action "右上角的导出按钮"` |
| `web/xiaohongshu/user_posts` | 慢滚动采集某个小红书用户主页的帖子卡片 | 否 | `python run.py showcase/web/xiaohongshu/user_posts -- --user-url <URL>` |
| `web/xiaohongshu/search_posts` | 慢滚动采集某个搜索词或 tag 下的帖子卡片 | 否 | `python run.py showcase/web/xiaohongshu/search_posts -- --keyword "露营"` |
| `web/xiaohongshu/post_detail` | 采集单篇帖子内可见文字、图片、视频和互动信息 | 否 | `python run.py showcase/web/xiaohongshu/post_detail -- --url <URL>` |

> `web/` 下的 Skill 来自真实系统的结构简化版，直接运行需要对应系统权限，**主要价值是提供结构参考**，照着把系统地址和字段替换成自己的即可。

## App（桌面应用）

暂无内置示例——桌面应用的模板截图跟每个人的系统、分辨率强相关，不适合直接复用别人截的图。
默认技术路线是图像模板匹配（`core.desktop.locate_and_click()`），不是截图发给 LLM 猜坐标，
参考 [app/README.md](app/README.md) 自己写一个。

## Office 文件

纯文件格式操作，不需要打开对应应用，不需要屏幕，可以直接跑在服务器上。

| Skill | 说明 | 需要 LLM | 运行命令 |
|---|---|---|---|
| `office/excel_toolkit` | 读写 Excel（`.xlsx`），JSON ↔ 表格互转 | 否 | `python run.py showcase/office/excel_toolkit/excel_toolkit -- --read data.xlsx` |
| `office/ppt_generator` | 从结构化内容生成 PPT（`.pptx`） | 否 | `python run.py showcase/office/ppt_generator/ppt_generator -- --output out.pptx --data '[...]'` |
| `office/word_report` | 从结构化内容生成 Word 文档（`.docx`） | 否 | `python run.py showcase/office/word_report/word_report -- --output out.docx --title "标题" --data '[...]'` |

> 都是"从模板/空白文档 + 结构化数据 → 生成文件"的最小示例，不支持复杂样式/图表/图片。真实场景通常需要基于公司现有模板（`Presentation("模板.pptx")` / `Document("模板.docx")`）继续编辑，而不是从空白文档开始，各自 README 里有说明。

---

## 贡献 Skill

欢迎提交 PR，将自建 Skill 贡献到 Showcase。要求：

- 放在对应类型目录下，例如 `showcase/web/workday/export_attendance.py`
- 实现 `main()` 函数，支持 `python run.py` 调用
- 不包含任何个人信息（账号、token、URL 从 `config.yaml` 读取）
- 在本文件表格中补充说明一行

详见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## Android

Android skills drive a connected Android device through ADB. This is the
"PC operates phone" route, separate from browser and desktop automation.

Android Skill 通过 ADB 操作已连接的 Android 设备，对应“电脑操作手机”的路线，和浏览器、桌面自动化是并列的框架能力。

| Skill | Description | Needs LLM | Command |
|---|---|---|---|
| `android/adb_basics` | List devices, screenshot, tap/swipe by ratio, send key events, push files, diagnostics | No | `python run.py showcase/android/adb_basics/adb_basics -- --devices` |
| `android/xiaohongshu_note` | Draft a Xiaohongshu note slowly through ADB; stops before final publish unless explicitly confirmed | No | `python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- --profile data/xhs_profile.json --dry-run` |

| Skill | 说明 | 需要 LLM | 运行命令 |
|---|---|---|---|
| `android/adb_basics` | 设备列表、截图、按比例点击/滑动、发送按键、推送文件、基础诊断 | 否 | `python run.py showcase/android/adb_basics/adb_basics -- --devices` |
| `android/xiaohongshu_note` | 通过 ADB 慢节奏起草小红书笔记；默认停在最终发布前，除非显式确认 | 否 | `python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- --profile data/xhs_profile.json --dry-run` |
