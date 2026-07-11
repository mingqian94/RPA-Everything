# integration/ — MCP / CLI / API 直连 Skill

这里放应用已提供结构化接入时的 Skill：官方 MCP Server、CLI 或 API。

这类 Skill 不依赖前台窗口、截图或视觉识别。它应明确检查安装、登录和权限前置条件，
然后调用结构化接口并验证返回结果。

## 新增一个应用接入

1. 建立 `integration/<应用名>/<动作>.py`，每个动作一个可运行 Skill。
2. 在同目录 README 写明所需 CLI/MCP、最低版本、账号权限和安全边界。
3. 密钥仅通过 `${secret:name}` 或本机环境变量引用，不能写进代码、日志、测试或文档。
4. 对发送、发布、审批、删除等外部副作用，继续遵守 `--confirm-external` 的显式确认规则。

只有当直连能力已经安装、认证并注册为可用 Skill 时，Harness 才能选它；否则回退到
`app/desktop/` 的 UI 自动化路线。
