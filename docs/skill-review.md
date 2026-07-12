# Skill Review and Safe Bug Reports

`harness/solidify` writes a neighboring manifest with a `review` section. Read it before a first run or scheduling.

Check the target platforms, required permissions, input assumptions, external-action risk, unresolved review reasons, and the checklist. `last_supervised_run` is `null` until an explicit `harness/supervise --run` attempt; it records only status, time, exit code, and whether evidence exists, never the evidence itself.

```bash
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json
python run.py harness/supervise -- --manifest skills/my_workflow.manifest.json --run
```

For a support report, first list runs and choose an id:

```bash
python run.py harness/runs -- --limit 20
python run.py harness/runs -- --show RUN_ID --export bug-report.json
```

The default export contains run metadata and step status only. It omits page text, URLs, screenshots, and result payloads. `--include-redacted-details` is opt-in and still redacts common secrets, phone numbers, and email addresses; review it before sharing.
