# 监督首跑与修复

`harness/solidify` 生成的 manifest 不是“可以直接定时运行”的许可。它记录了 trace 的证据等级、风险 review、选路和监督运行规则。

## 首跑

```bash
# 只检查前置条件，不执行 Skill
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json

# 人工看护下运行一次
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json --run
```

监督运行会先检查 trace 所需的 Chrome CDP 或 Android ADB。manifest 仍有 review 原因、或前置条件失败时，命令会停止，不会尝试绕过限制。

## 结果与漂移

- 进程退出码为零，只说明脚本成功结束；仍需核对业务成功信号、导出文件或可见结果。
- 出现 selector、模板、UI 节点找不到或超时等疑似漂移时，命令返回 `needs_repair`，附带脱敏后的最小错误证据。
- 将返回的 `repair_task.goal` 交给 Harness/Agent 修复。它要求从原 trace 开始，优先选择 MCP/CLI/API、DOM、UI 节点或模板，不允许在修复时执行最终外部操作。

截图、URL、Cookie、客户数据或完整页面文本不自动写入 repair task；如需额外证据，应在用户审阅后单独提供。
