# RPA-Everything 中文速上手

目标：不用先学编程。你负责讲清楚工作怎么做，Harness Agent 帮你规划、探索并导出一个可复用的 Skill。

## 1. 安装并完成体检

让 Codex、Claude 等能执行命令的 Agent 自己完成安全安装时，直接使用：

```powershell
powershell -ExecutionPolicy Bypass -File tools\agent-bootstrap.ps1
```

macOS / Linux：

```bash
sh tools/agent-bootstrap.sh
```

它只安装依赖、创建缺失的配置模板、运行体检和本地 demo；不会填写 Key、启动登录、打开浏览器或执行外部操作。可直接交给 Agent 的完整提示词见 [Agent 自助安装](docs/agent-bootstrap.zh-CN.md)。

手动安装仍可使用：

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

## 2. 无 Key 先看完整生命周期

在填写 LLM Key 前，可以运行这个只读预览：

```bash
python run.py harness/demo
```

它只读取仓库内置 trace，展示 `doctor → runtime → replay --dry-run → solidify` 的产物链；不联网、不打开浏览器、不写文件，也不会执行外部操作。

## 3. 先把工作讲清楚

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

## 4. 导出、检查、再运行

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

如果已导出一份真实执行轨迹 JSON，可以让 Agent 或 CLI 进一步固化：

```bash
python run.py harness/solidify -- --trace data/outputs/trace.json --output skills/my_workflow.py
```

它会生成同名 `.manifest.json`。只有 `ready_for_supervised_run` 才表示可以在人工看护下首跑；这不等于可以直接定时运行或执行最终外部操作。

先检查前置条件，再在人工看护下首跑：

```bash
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json --run
```

`supervise` 遇到 selector、模板或 UI 节点可能漂移时会停止并返回脱敏证据和 repair task；命令成功退出后仍需人工核对业务结果。详见 [监督首跑与修复](docs/supervised-run.zh-CN.md)。

## 本地账号和数据

不要把密码、Token、Cookie 或客户数据写进 Skill。复用密钥时，在本机环境变量设置 `RPA_SECRET_CRM_PASSWORD`，并在配置中引用 `${secret:crm-password}`。日志和 trace 会对常见敏感字段、手机号和邮箱脱敏，但分享前仍需人工检查。

## 有真实外部操作时

发消息、发布内容、审批、付款、删除或修改远端数据，必须在最后一步前停下。按 [外部操作确认单](docs/external-action-confirmation.zh-CN.md) 明确目标和范围，再显式使用 `--confirm-external`。这不是跳过人工审核，而是记录人工审核已经完成。

更多能力与示例见 [README.zh-CN.md](README.zh-CN.md) 和 [AGENTS.md](AGENTS.md)。
