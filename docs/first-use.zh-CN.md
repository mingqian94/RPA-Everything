# 十分钟完成第一个有用任务

本教程会把公开网页中的 HTML 表格导出为 CSV。不需要 API Key、登录或任何外部写入操作；它会访问公开网站，因此需要 Chrome 和网络连接。

## 1. 安装并体检

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
python run.py harness/doctor
```

macOS：

```bash
sh tools/setup.sh
python run.py harness/doctor
```

先处理必需项的 `FAIL`。本任务不需要 Android 或 iPhone，相关 `WARN` 可以忽略。

## 2. 启动专用浏览器

```powershell
tools\start_chrome.bat
```

```bash
sh tools/start_chrome.sh
```

保持这个浏览器窗口打开。它使用独立的 RPA profile，不会改动你日常 Chrome 的 profile。

## 3. 导出公开表格

```bash
python run.py showcase/web/extract_table/extract_table -- --url "https://www.w3schools.com/html/html_tables.asp" --output first-use-table.csv
```

预期结果：终端提示 CSV 已保存，根目录出现 `first-use-table.csv`，里面有表格数据。完成后可以删除该文件。

## 4. 你刚刚验证了什么

你已完成运行环境安装、专用浏览器连接、只读网页任务和本地结果保存。整个过程没有调用 LLM、没有使用账号，也没有真实业务外部操作。

下一步用[任务描述模板](workflow-template.zh-CN.md)描述一个重复工作。任何新流程都先用 `--dry-run` 看计划；发布、发送、审批、付款、删除或修改远端数据必须保留显式人工确认。
