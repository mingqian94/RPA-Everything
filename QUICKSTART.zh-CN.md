# RPA-Everything 中文速上手

目标：不用先学编程。你负责讲清楚工作怎么做，Harness Agent 帮你规划、探索并导出一个可复用的 Skill。

## 1. 安装并完成体检

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
python run.py harness/doctor --fix
```

macOS / Linux：

```bash
sh tools/setup.sh
python run.py harness/doctor --fix
```

`--fix` 只会创建缺失的 `config.yaml`，不会写入 API Key、启动浏览器或执行任何外部操作。打开 `config.yaml`，填写 `llm.api_key` 和 `llm.model` 后，再运行一次：

```bash
python run.py harness/doctor
```

Android 和 iPhone 的 `WARN` 是可选能力提示；暂时不做手机自动化时可以忽略。

## 2. 先把工作讲清楚

复制 [任务描述模板](docs/workflow-template.zh-CN.md)，补全目标系统、开始前的准备、人工步骤、成功标准和禁止事项。

第一次一定先只看计划：

```bash
python run.py harness/agent -- --goal "把我描述的工作流先规划出来，不要提交、发布、发送或删除任何内容" --dry-run
```

浏览器任务先启动专用 Chrome，并在里面登录目标系统：

```powershell
tools\start_chrome.bat
```

```bash
sh tools/start_chrome.sh
```

## 3. 导出、检查、再运行

确认计划合理后，导出为一个可以继续完善的 Skill：

```bash
python run.py harness/agent -- --goal "按我描述的步骤探索并导出 Skill，最终提交或发布前必须停下" --export skills/my_workflow.py
```

命令会生成两个文件：

- `skills/my_workflow.py`：需要 review 并补齐 `TODO` 的可执行脚本。
- `skills/my_workflow.README.md`：目标、运行方式、执行前检查和外部操作风险提示。

检查脚本后运行：

```bash
python run.py skills/my_workflow
```

## 有真实外部操作时

发消息、发布内容、审批、付款、删除或修改远端数据，必须在最后一步前停下。按 [外部操作确认单](docs/external-action-confirmation.zh-CN.md) 明确目标和范围，再显式使用 `--confirm-external`。这不是跳过人工审核，而是记录人工审核已经完成。

更多能力与示例见 [README.zh-CN.md](README.zh-CN.md) 和 [AGENTS.md](AGENTS.md)。
