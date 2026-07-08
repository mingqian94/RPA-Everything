# Security Policy

RPA-Everything is a local automation framework. It can operate browsers, desktop apps, Android devices, files, and user-created Skills. Treat it as a tool that can take real actions on your machine.

## Trust Model

The framework has two execution modes:

- **Exploration mode**: an LLM can inspect pages/screens and decide which tools to call. This is powerful but exposed to prompt injection from web pages, app content, documents, and screenshots.
- **Execution mode**: a saved Skill runs as normal Python code without LLM reasoning. This is the preferred mode for repeated production tasks.

When possible, explore once, review the generated Skill, then run the reviewed Skill repeatedly.

## Secrets And Local Data

- Keep real secrets in `config.yaml` or environment variables. `config.yaml` is git-ignored.
- Do not hardcode API keys, cookies, session tokens, account names, phone numbers, customer data, or private URLs in Skills, tests, docs, or screenshots.
- Use placeholder examples such as `<your-api-key>` in docs.
- Review files under `logs/` and `data/outputs/` before sharing. They may contain page text, app text, URLs, task results, or screenshots.

## External Side Effects

The Harness marks capabilities with `side_effect_level`:

- `none`: read-only or local extraction.
- `local`: local machine/device checks or local file operations.
- `external_draft`: prepares content in an external app but should stop before final publish/submit.
- `external_commit`: may publish, send, approve, pay, delete, modify remote data, or otherwise commit a real external action.
- `unknown`: not enough information; treat as risky.

For commit-like actions, Harness blocks execution unless `--confirm-external` is explicitly passed. Do not bypass this for workflows that publish, send, approve, pay, delete, or change production systems.

## Browser And Prompt Injection

Untrusted websites can try to influence the LLM through visible or hidden page content. During exploration:

- Watch tool calls in the MCP client before approving them.
- Be especially careful with `skill_save`, `skill_run`, `orchestrate`, desktop clicks, Android taps, and file writes.
- Do not let the model follow instructions found on a web page that conflict with your goal.
- Review generated code before running it.

## Desktop And Android Automation

Desktop and Android tools can click real UI, type text, push files, and trigger app actions.

- Prefer UI selectors where available (`android_dump_ui`, `android_tap_element`) before raw coordinates.
- Prefer `--dry-run` for showcase Skills that support it.
- Keep final publish/send/approve steps separate and guarded by explicit confirmation.
- For Android unicode input, ADBKeyboard may be enabled temporarily and then restored. Verify the device input method if a run is interrupted.

## Generated Skills

Generated Skills are plain Python scripts and should be reviewed like any other code:

- Check imports, subprocess calls, file writes, network requests, and final click/submit actions.
- Keep secrets out of source files.
- Add explicit arguments for user-provided data.
- Prefer writing results to `data/outputs/<skill>/<timestamp>/` or a user-provided `--output` path.

## Pre-Commit Checks

Before committing or publishing changes, run:

```bash
ruff check .
pytest
```

Scan changed files for secrets and personal data:

```bash
rg -n -i "(api[_-]?key|secret|token|password|passwd|authorization|bearer|x-api-key|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|[[:alnum:]._%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}|1[3-9][0-9]{9})"
```

Expected safe matches include placeholder environment variable names, documentation examples, and code variable names. Investigate any real value.

## Supported Platforms

Windows and macOS are the currently exercised desktop targets. Android ADB is the main mobile automation path. Linux and HarmonyOS may work for some primitives but should be treated as unverified until tested.

## Reporting

This project is not yet operating as a public security response program. For private/internal use, report issues directly to the repository owner and include:

- affected tool or Skill,
- exact command or MCP call,
- expected vs actual behavior,
- whether real external side effects occurred,
- relevant logs with secrets redacted.
