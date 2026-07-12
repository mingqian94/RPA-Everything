# Skill 审阅与安全故障报告

`harness/solidify` 会生成同名 manifest，其中的 `review` 是首跑和定时前必须阅读的摘要。

检查目标平台、所需权限、输入假设、外部动作风险、未解决的 review 原因和 checklist。只有显式执行一次 `harness/supervise --run` 后，`last_supervised_run` 才会从 `null` 变为首跑状态；它只记录时间、状态、退出码和是否存在证据，不会把证据正文写回 manifest。

```bash
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json --run
```

需要提交故障时，先列出运行记录并选择 id：

```bash
python run.py harness/runs -- --limit 20
python run.py harness/runs -- --show RUN_ID --export bug-report.json
```

默认报告只包含运行元数据和步骤状态，不含页面文本、URL、截图或结果 payload。`--include-redacted-details` 是显式可选项，仍会脱敏常见密钥、手机号和邮箱；分享前请再次人工检查。
