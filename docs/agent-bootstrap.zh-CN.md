# Agent 自助安装

适用于 Codex、Claude Code 或其他可在本机执行命令的 Agent。目标是让 Agent 自己完成依赖安装、体检和安全 demo；账号、密钥和最终外部操作仍由用户控制。

## 交给 Agent 的提示词

```text
请在 RPA-Everything 项目根目录执行安全自助安装。

1. 先阅读 AGENTS.md 和 SECURITY.md。
2. Windows 运行：powershell -ExecutionPolicy Bypass -File tools\agent-bootstrap.ps1。
   macOS/Linux 运行：sh tools/agent-bootstrap.sh。
3. 如 config.yaml 仍缺少 llm.api_key 或 llm.model，只报告需要我填写；不要猜测、索取、写入或打印任何密钥。
4. 阅读 python run.py harness/demo 的结果，确认它没有联网、没有外部操作、没有打开浏览器。
5. 安装完成后只执行一个 --dry-run 的只读任务规划；不要提交、发布、发送、审批、付款、删除或修改远端数据。
6. 输出：已完成的步骤、未满足的前置条件、下一条安全命令。不要自行安装第三方 MCP、上传本地文件或复用浏览器 Cookie。
```

## Bootstrap 的边界

- 会安装 Python 依赖和 Playwright Chromium，并在缺失时创建 `config.yaml` 模板。
- 不会写入 LLM/API Key，不会打开登录窗口，不会启动专用 Chrome，也不会调用真实业务系统。
- `doctor` 可能因未填写模型配置返回失败；这是预期状态，不影响本地 demo。
- 完成配置后，真实任务仍应先用 `--dry-run`，再由用户审核导出的 Skill。
