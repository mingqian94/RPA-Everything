# Demo: Browser Table Extraction

## Goal

Show a browser task using a public page, DOM-based extraction, and a saved JSON output. This is a safe read-only recording.

## Prepare

1. Run `tools\start_chrome.bat` on Windows or `sh tools/start_chrome.sh` on macOS/Linux.
2. Run `python run.py harness/doctor` and ensure browser readiness is OK.

## Record

```bash
python run.py showcase/web/extract_table/extract_table -- --url https://www.w3schools.com/html/html_tables.asp --output data/outputs/demo-browser-table.json
```

Capture three frames: the command, the resulting JSON file, and `python run.py harness/runs -- --skill web/extract_table --limit 1`.

## Evidence

- `data/outputs/demo-browser-table.json`
- Structured log entry returned by `harness/runs`

Do not record a logged-in page or expose a browser profile.
