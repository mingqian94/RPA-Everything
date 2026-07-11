# Demo: Harness Trace Solidification

## Goal

Show the framework's main promise: Agent exploration becomes a reviewable Skill rather than an Agent repeatedly operating the same UI.

## Record

```bash
# First: run an approved read-only task and save its real trace.
python run.py harness/agent -- --goal "Extract a public table. Do not submit, publish, send, or modify anything." --trace-json data/outputs/demo-trace.json

# Then: generate and assess the deterministic draft.
python run.py harness/solidify -- --trace data/outputs/demo-trace.json --output skills/demo_table_extract.py
```

## Evidence

- `data/outputs/demo-trace.json`
- `skills/demo_table_extract.py`
- `skills/demo_table_extract.manifest.json`

Show the manifest status on screen. If it says `needs_review`, explain the reason and stop; do not edit the recording to imply production readiness.
