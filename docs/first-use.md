# First Useful Task in Ten Minutes

This walkthrough extracts a public HTML table into a CSV file. It needs no API key, login, or external write. It does open a public website and requires Chrome plus a network connection.

## 1. Install and check

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
python run.py harness/doctor
```

macOS:

```bash
sh tools/setup.sh
python run.py harness/doctor
```

Resolve required `FAIL` items. Android and iPhone warnings are not needed for this task.

## 2. Start the dedicated browser

```powershell
tools\start_chrome.bat
```

```bash
sh tools/start_chrome.sh
```

Keep that browser open. It uses a separate RPA profile and does not change your normal Chrome profile.

## 3. Extract a public table

```bash
python run.py showcase/web/extract_table/extract_table -- --url "https://www.w3schools.com/html/html_tables.asp" --output first-use-table.csv
```

Expected result: the terminal reports that a CSV was saved, and `first-use-table.csv` contains the table rows. Delete the file when you are done.

## 4. What you just proved

You installed the runtime, connected the dedicated browser, performed a read-only browser task, and saved a local result. No LLM call, account, or external business action was involved.

Next, use the [workflow template](workflow-template.zh-CN.md) to describe one repeated task. Start every new workflow with `--dry-run`; keep publishing, sending, approval, payment, deletion, and remote changes behind explicit confirmation.
