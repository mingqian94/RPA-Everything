# RPA-Everything

**English** | [中文](README.zh-CN.md)

![CI](https://github.com/mingqian94/RPA-Everything/actions/workflows/ci.yml/badge.svg)

An AI-powered automation framework for everyone who works with repetitive computer tasks: describe the task in natural language, and AI turns it into a reusable script.

> **Not a general-purpose RPA platform.** It's a lightweight workflow: *AI writes the script, you review it, the script runs on a schedule.* Built for individuals and teams who repeatedly perform the same operations across web apps, desktop apps, and office documents.

> **For AI agents**: if you are a desktop agent such as Claude Desktop or Codex, read [AGENTS.md](AGENTS.md) for integration instructions.

---

## Fastest Path For Non-Developers

The goal is not to learn programming. Describe the work steps clearly, let the Agent generate the Skill, then run the Skill directly.

### 1. One-command setup

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

macOS / Linux:

```bash
sh tools/setup.sh
```

After setup, open `config.yaml` and fill `llm.api_key` / `llm.model`.

### 2. Check readiness

```bash
python run.py harness/doctor
```

Fix `FAIL` items. Android/iPhone `WARN` items are optional until you need phone automation.

### 3. Describe the workflow and generate a Skill

Use [the workflow template](docs/workflow-template.zh-CN.md) if you need a structure, then run:

```bash
python run.py harness/agent -- --goal "Plan my described workflow first. Do not submit, publish, or send anything." --dry-run
python run.py harness/agent -- --goal "Run through my described workflow once and export a reusable Skill." --export skills/my_workflow.py
python run.py skills/my_workflow
```

For browser tasks, start the dedicated Chrome first:

```bash
tools\start_chrome.bat     # Windows
sh tools/start_chrome.sh   # macOS
```

---

## How it differs from similar tools

| Tool | Positioning | Limitation |
|---|---|---|
| Playwright / Selenium | Developers write test scripts | Requires coding — non-engineers can't use it |
| n8n / Zapier | No-code workflow orchestration | Breaks on complex UI operations or private systems |
| RPA platforms (UiPath etc.) | Enterprise record-and-replay | Heavy, expensive, weak AI capabilities |
| Claude Computer Use | AI looks at the screen, computes coordinates, moves the mouse | The model must re-understand the UI on every run: token cost per execution, and LLMs guessing coordinates from screenshots is inherently unreliable (this project hit real mis-clicks caused by Retina coordinate-system mismatches) |
| **This framework** | AI generates the script through conversation; the script runs on a schedule | Exploration phase requires a Claude API key |

**The core trade-off**: use AI to lower the barrier of *writing* automation, but never depend on AI at *execution* time — once a workflow is solidified it's a plain script: zero AI cost, high stability.

### vs. Claude Computer Use

In one sentence: **Computer Use is "AI does it by hand every time"; this framework is "AI acts exactly once (exploration), then hands off to a deterministic script."**

Computer Use lets the model look at screenshots, judge coordinates, and click the mouse itself — a general capability, great for genuinely one-off tasks whose steps can't be known in advance. But when the same task repeats (checking leave balance daily, processing approvals hourly), making the model re-understand the UI every time is both token-hungry and fragile: coordinate precision from screenshots is limited, and physical-vs-logical pixel mismatches on Retina displays are a pitfall we hit in practice.

This framework splits the capability into two phases. **Exploration**: AI (screenshot analysis or browser DOM operations) figures out the steps once. **Solidification**: those steps become a deterministic script — desktop flows locate elements via image template matching (`locate_and_click()` in `core/desktop.py`) instead of LLM coordinate guessing; browser flows use CSS/XPath selectors instead of vision. After solidification the AI exits the stage: the script goes straight into crontab — zero AI cost, reproducible results, reviewable code.

A real comparison: our Feishu approval automation was first tested with the Harness (screenshot + LLM coordinate clicking — the same pattern as Computer Use) and failed twice — once on a hung API request, once mis-clicking another app due to coordinate drift. Rewritten as a fixed script with template matching, the same batch of real approval tickets passed 3/3, finished in 18 seconds, with zero AI calls.

---

## Workflow

```
Describe the task (natural language)
    ↓
Claude Desktop + MCP Server
    ↓  screenshots, actions, code generation
Looks right? → Save as a Skill
    ↓
python run.py <skill>   # scheduled / on-demand, no AI involved
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           User (conversation / CLI)               │
│     Claude Desktop / python run.py <skill>        │
├──────────────────────────────────────────────────┤
│           MCP Server  mcp_server.py               │
│  Conversation-driven: NL → Claude → tool calls    │
│  Solidifiable: generated code saved as a Skill    │
├──────────┬───────────────────┬───────────────────┤
│ Showcase │   Your own Skills │   Direct script    │
│ examples │  saved from chat  │  python run.py     │
└──────────┴───────────────────┴───────────────────┘
                      ↓
         core / connectors (shared foundation)
```

---

## Directory layout

```
rpa-everything/
├── core/                    # Generic capability layer (business-agnostic)
│   ├── browser.py           # Web automation (Playwright, reuses your logged-in Chrome); is_logged_in() for httpOnly session cookies
│   ├── intercept.py         # Capture API responses via fetch/XHR hooks (for pages that load data by background requests)
│   ├── desktop.py           # Desktop automation (macOS: screencapture + pyautogui; Windows: pywinauto)
│   ├── android.py           # Android automation through ADB (PC operates phone)
│   ├── llm.py               # Claude API (decisions / content generation / vision fallback)
│   ├── agent.py             # Agentic loop (run_browser / run_desktop / run_android)
│   ├── tools.py             # Single source of truth for tool schemas (shared by agent loop & MCP Server)
│   ├── skills.py            # Skill discovery & saving (shared by run.py / MCP / generator)
│   ├── config.py            # Config access (config.yaml + environment variables)
│   ├── logger.py            # Structured execution logs (auto-pruned)
│   ├── notify.py            # Failure notifications (Feishu webhook)
│   └── verify.py            # Post-run verification (LLM-as-judge: screenshot + SOP → ok/fail)
│
├── connectors/              # System connectors (opt-in)
│   ├── feishu.py            # Feishu (Lark) API
│   └── http.py              # Generic HTTP
│
├── harness/                 # Harness Agent (high-level goal → plan + execute)
│   └── agent.py             # LLM planning (structured tool-use output) → concurrent subagents
│
├── showcase/                # Skill examples (one per technical approach, see ARCHITECTURE.md)
│   ├── web/
│   │   ├── extract_table/   # Generic web table extraction (Browser DOM)
│   │   ├── click_by_vision/ # Vision-based clicking (Browser + LLM Vision)
│   │   └── xiaohongshu/     # Xiaohongshu user/search/detail crawling showcases
│   ├── app/
│   │   └── template_click/  # Image-template-matching click (minimal desktop example, bring your own template)
│   ├── android/
│   │   ├── adb_basics/      # Android ADB basics: devices, screenshots, taps, swipes, push files
│   │   └── xiaohongshu_note/# Xiaohongshu note draft flow: slow ADB steps, stops before final publish
│   └── office/              # Pure file-format operations — no screen needed, server-friendly
│       ├── excel_toolkit/   # Excel read/write (openpyxl)
│       ├── ppt_generator/   # Generate PPT from structured content (python-pptx)
│       └── word_report/     # Generate Word documents (python-docx)
│
├── skills/                  # Your own Skills (commit them or keep them private)
│   └── feishu_project_daily.py  # Feishu project daily report (API interception, scheduled)
│
├── assets/                  # Image templates for desktop automation (subdirectory per system)
├── sops/                    # SOP documents (used by Harness verify; add your own)
│
├── tools/
│   ├── generate_skill.py    # Skill generator (screenshot + description → code)
│   ├── cron_helper.sh       # Generate a crontab line (macOS / Linux)
│   ├── cron_helper.ps1      # Generate a schtasks command (Windows)
│   ├── start_chrome.sh      # Launch debug Chrome (macOS)
│   └── start_chrome.bat     # Launch debug Chrome (Windows)
│
├── logs/                    # Execution logs (auto-generated, 30-day retention by default)
├── config.yaml              # Config template
├── mcp_server.py            # MCP Server entry point
├── run.py                   # Unified runner (`rpa` command after pip install -e .)
└── pyproject.toml
```

---

## Where Skills can run: local vs. server

Different Skill types have different environment requirements:

| Skill type | Typical scenario | Server-friendly? | Notes |
|---|---|---|---|
| **API** | Feishu API, custom webhooks | ✅ Yes | Pure HTTP, no UI dependency |
| **Office files** | Excel/PPT/Word read & write | ✅ Yes | Pure file-format operations, the app never opens |
| **Browser** | CRM queries, HR systems | ⚠️ Needs local Chrome | Depends on your logged-in Chrome session |
| **Desktop** | Feishu/DingTalk native apps | ❌ Local only | Needs a physical screen and foreground window |
| **Android phone** | Phone apps, mobile-only flows | ⚠️ Needs local ADB connection | PC drives a real Android device through ADB |

**Deployment advice:**

```
Unattended scheduled automation
  → API-type Skills only → deploy to a server, trigger via cron

UI interaction required
  → run on your local machine, or a dedicated always-on box (Mac Mini / Windows PC)
```

When mixing API and UI Skills, split the flow: run UI steps locally, publish results via API.

---

## Supported automation targets

| Application type | Examples | Approach | Module |
|---|---|---|---|
| **APIs** | Feishu, custom HTTP endpoints | Direct HTTP calls | `connectors/` |
| **Office files** | Excel, PPT, Word reports | Direct file-format read/write (openpyxl / python-pptx / python-docx), app never opens | `showcase/office/` |
| **Web apps** | CRM, HR systems, campus portals | Playwright DOM operations | `core/browser.py` |
| **Electron apps** | Feishu/DingTalk desktop | Playwright via debug port | `core/browser.py` |
| **Windows native apps** | Local desktop software | pywinauto UI Automation | `core/desktop.py` |
| **Any desktop app (fallback)** | Feishu, DingTalk, etc. | PyAutoGUI + image template matching; CJK input via clipboard paste | `core/desktop.py` |
| **Android apps** | Mobile apps, phone-only workflows | ADB screenshots/taps/swipes/keyevents/file push | `core/android.py` |

### Element-location fallback chain

**Browser:**
```
CSS/XPath selectors  →  fails  →  Claude Vision  →  fails  →  human confirmation
  milliseconds, free           billed per token         last resort
```

**Desktop:**
```
Image template matching (locate_and_click)  →  fails  →  Claude Vision coordinate guess  →  fails  →  human confirmation
   free, deterministic, tolerates small scale drift        billed per token, less precise
```

Template matching beats LLM coordinate guessing: for stable-looking buttons/icons (Approve, nav items), take one screenshot, save it as a template under `assets/<system>/`, and let `core.desktop.locate_and_click()` find it precisely every time — no LLM involved. This also sidesteps the Retina problem where the LLM reads *physical*-pixel coordinates from a screenshot but clicks are interpreted in *logical* pixels (`physical_to_logical()` in `core/desktop.py` handles that conversion, but template matching avoids coordinate guessing at the root).

---

## Quick start

### 1. Install dependencies

**System requirements (beyond Python packages):**

| Dependency | Purpose | Required? |
|---|---|---|
| **Google Chrome** | Runtime for browser Skills (reuses your logged-in session) | For browser Skills |
| Python 3.11+ | Runs the framework | Yes |

Chrome: https://www.google.com/chrome/

```bash
pip install -r requirements.txt
playwright install chromium

# Optional: editable install to get the `rpa` CLI entry point
pip install -e .
```

**macOS desktop automation** (driving native apps like Feishu/DingTalk) additionally needs:

```bash
# pyautogui requires Homebrew Python 3.11+ (system Python 3.9 won't work)
brew install python@3.12
/opt/homebrew/bin/python3.12 -m pip install pyautogui --break-system-packages
```

Also grant your terminal Screen Recording permission in System Settings → Privacy & Security.

### 2. Configure

Copy `config.yaml` and fill it in, or use environment variables:

```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

### 3. Launch Chrome (reusing your logged-in session)

Run the launcher script. **Log in to your target systems once in this browser; subsequent runs need no login:**

```bash
# macOS
sh tools/start_chrome.sh

# Windows
tools\start_chrome.bat
```

The script uses a dedicated profile (`~/.chrome-rpa-profile`) so it never touches your daily Chrome — both can run side by side.

### 4. Run a Skill

```bash
# List all available Skills
python run.py

# Run a showcase example
python run.py showcase/office/excel_toolkit/excel_toolkit -- --read data.xlsx

# Run your own Skill
python run.py skills/my_skill
```

### 5. Schedule a Skill

**macOS / Linux** (crontab):

```bash
# Usage: sh tools/cron_helper.sh <skill path> <cron expression>
sh tools/cron_helper.sh skills/my_skill "0 9 * * 1-5"
```

The script prints a complete crontab line (with PYTHONPATH, python path, and log redirection) — paste it via `crontab -e`.

**Windows** (Task Scheduler):

```powershell
# Every weekday at 09:00
powershell -File tools\cron_helper.ps1 skills/my_skill 09:00 -Weekdays

# Every 30 minutes
powershell -File tools\cron_helper.ps1 skills/my_skill -EveryMinutes 30
```

The script prints a complete `schtasks /Create` command — run it in an elevated PowerShell.

### 6. Generate a new Skill (no coding)

```bash
python tools/generate_skill.py
```

Open the target page → describe the operation → AI generates the code → save and run.

### 7. Harness Agent (explore → solidify into a Skill)

The Harness is an **exploration tool, not a production executor**. Use it to quickly verify "can this be automated, and what are the steps?" — then solidify the flow into a plain Skill that runs on a schedule. After solidification the Harness exits the picture: subsequent runs cost zero AI.

**Solidification path:**

```bash
# Step 1: see how the LLM decomposes the goal, confirm the direction
python run.py harness/agent -- --goal "extract the table from this page" --dry-run

# Step 2: provide an SOP document; a screenshot is verified against it after the run
python run.py harness/agent -- --goal "extract the table from this page" --sop sops/my_task/extract.md

# Step 3: export a skeleton script (auto-generated, with step structure and TODOs)
python run.py harness/agent -- --goal "extract the table from this page" --export skills/my_task_daily.py

# Step 4: execute once, then export the actual tool-call trace as a first-draft Skill
python run.py harness/agent -- --goal "extract the table from this page" --export-trace skills/my_task_daily.py

# Optional: export replayable JSON trace, then dry-run replay it
python run.py harness/agent -- --goal "extract the table from this page" --trace-json data/outputs/trace.json
python run.py harness/replay -- --trace data/outputs/trace.json --dry-run

# Optional: run the static Harness eval set
python evals/run.py

# Optional: run a non-destructive Android real-device smoke test
python run.py showcase/android/smoke_test/smoke_test -- --output data/outputs/android_smoke.json

# Optional: also verify file push by creating and deleting a tiny probe file
python run.py showcase/android/smoke_test/smoke_test -- --include-file-check --output data/outputs/android_smoke.json

# Step 4: open skills/my_task_daily.py, replace the TODOs with deterministic Playwright code
# Step 5: verify
python run.py skills/my_task_daily

# Step 6: schedule it — the Harness is no longer needed
sh tools/cron_helper.sh skills/my_task_daily "0 9 * * 1-5"
```

| | Harness (exploration) | Plain Skill (production) |
|---|---|---|
| Steps come from | LLM planning at runtime | Hard-coded |
| Execution | agentic loop, reasoning each step | deterministic script |
| AI cost | every run | zero |
| Best for | first walkthrough, feasibility check | scheduled production runs |

**Extending the Harness:** add reusable agent capabilities in `core/capabilities.py`. Runnable scripts under `showcase/` and `skills/` are also auto-discovered as `skill:<path>` capabilities, so the planner can call solidified Skills directly when the goal matches.

---

## Writing a new Skill

Create a `.py` file under `skills/` with a `main()` function:

```python
from core.browser import open_page
from core.logger import SkillLogger
from core.config import get

async def main():
    log = SkillLogger("my_skill")

    async with open_page(get("systems.crm.url")) as page:
        log.step("Open CRM")
        await page.click("text=Export")
        log.step("Click export")

    log.finish()
```

### When to bring in the LLM

| Scenario | Approach |
|---|---|
| Fixed flow, stable pages | Pure Playwright, no LLM |
| Selector broke, UI changed | `vision.find_element()` → `llm.find_element()` |
| Personalized message copy | `llm.generate()` |
| Conditional judgment, state recognition | `llm.decide(screenshot)` |

---

## MCP Server — conversation-driven automation

The MCP Server is the conversational entry point: drive automation and explore new scenarios by talking to Claude, no code required.

### Connect to Claude Desktop

Edit `~/.claude/claude_desktop_config.json` (create it if missing):

```json
{
  "mcpServers": {
    "rpa-everything": {
      "command": "python",
      "args": ["/absolute/path/to/rpa-everything/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop; the `rpa-everything` toolbox appearing in the sidebar means you're connected.

### Available tools (24)

Browser, desktop, and Android tools share one schema definition with the agentic loop (`core/tools.py`), so they can't drift apart.

**Browser**

| Tool | Description |
|---|---|
| `browser_navigate` | Open a URL |
| `browser_screenshot` | Screenshot the current page |
| `browser_click` | Click an element (by text / CSS selector) |
| `browser_type` | Type into an input field |
| `browser_extract_text` | Extract page text |
| `browser_extract_table` | Extract a table (returns JSON) |
| `browser_evaluate` | Run JavaScript in the page |

**Desktop**

| Tool | Description |
|---|---|
| `desktop_screenshot` | Screenshot the whole screen |
| `desktop_click` | Click screen coordinates (logical pixels, Retina-aware) |
| `desktop_type` | Type text (CJK goes through clipboard paste) |
| `desktop_hotkey` | Send a keyboard shortcut, e.g. `command+v`, `ctrl+c` |
| `desktop_find_click` | Screenshot → LLM vision locates the element → click |

**Android**

| Tool | Description |
|---|---|
| `android_devices` | List connected ADB devices |
| `android_screenshot` | Screenshot a connected Android device |
| `android_tap` | Tap by pixels or normalized screen ratio |
| `android_dump_ui` | Dump UIAutomator nodes as JSON |
| `android_tap_element` | Tap by text, resource-id, or content-desc |
| `android_swipe` | Swipe by pixels or normalized screen ratio |
| `android_key` | Send an Android keyevent, e.g. `KEYCODE_BACK` |
| `android_type` | Type text; `unicode=true` uses ADBKeyboard broadcast input and restores the previous IME when possible |
| `android_push_file` | Push a file to the device, optionally trigger media scan |
| `android_diagnostics` | Check ADB availability, device state, hardware serial, resolution, screenshot, UIAutomator, ADBKeyboard, and optional input/file-push probes |

**iPhone**

| Tool | Description |
|---|---|
| `ios_devices` | List iPhones visible to `pymobiledevice3`; WiFi discovery is best-effort |
| `ios_diagnostics` | Check iPhone semi-automation prerequisites |
| `ios_copy_text` | Copy text to the iPhone clipboard |
| `ios_launch_app` | Launch an iPhone app by bundle id, for example `com.tencent.xin` |
| `ios_screenshot` | Capture an iPhone screenshot for evidence |

The iPhone path is semi-automation: it can prepare the phone, copy text, open an app, and capture evidence. It does not claim remote touch or final publish/approval automation without a separately verified WDA/XCUITest/CoreDevice touch path.

**Skill management**

| Tool | Description |
|---|---|
| `skill_list` | List all available Skills |
| `skill_run` | Run a saved Skill |
| `skill_save` | Save conversation-generated code as a Skill |

**Harness**

| Tool | Description |
|---|---|
| `orchestrate` | Takes a natural-language goal, plans and executes multiple Skills; supports `dry_run` (plan only), `export` (skeleton script), `export_trace` (first-draft script from actual tool calls), `sop` (post-run screenshot verification) |

Skill run artifacts should go under `data/outputs/<skill>/<timestamp>/` by default. Use `--output <path>` when a stable path is required by another system.

### Typical flows

**Exploring a new scenario:**
1. Open Claude Desktop with the `rpa-everything` tools enabled
2. Describe the goal: "Check which CRM follow-ups are due today"
3. Claude screenshots, operates the page, returns results
4. Looks right? "Save this as a Skill" → code lands in `skills/`

**Driving a desktop app (Feishu example):**
```
You: Post a message in a Feishu group: "Today's progress update…"
Claude: desktop_screenshot → locate the input box → desktop_click → desktop_type → screenshot to confirm
```

### Security boundaries

See [SECURITY.md](SECURITY.md) for the full policy: secrets, local data, prompt injection, external side effects, desktop/Android risks, and pre-commit scans.

The MCP Server hands the LLM the ability to *operate your screen and write & run code*. That means **anything the model reads — including web page content — can indirectly influence its tool calls** (prompt injection). Keep in mind:

- When Claude operates **untrusted web pages** during exploration, watch the `skill_save` / `skill_run` calls it makes — don't blindly approve Claude Desktop's tool-confirmation dialogs
- `skill_save` can only write inside the `skills/` directory; review saved code before running it
- Solidified Skills are plain scripts that never touch an LLM, so this risk doesn't apply to them — one more reason this framework insists on separating exploration from production

---

## Showcase status

| Skill | Approach | Status | Notes |
|---|---|---|---|
| `showcase/web/extract_table` | Browser DOM | ✅ Runnable | `--url https://www.w3schools.com/html/html_tables.asp` |
| `showcase/web/click_by_vision` | Browser + LLM Vision | ✅ Runnable | `model: global.anthropic.claude-sonnet-4-6` in config.yaml |
| `showcase/web/xiaohongshu/user_posts` | Browser DOM crawl | ✅ Runnable | Slow-scroll a user's posts; `--user-url <URL> --output data/xhs_user.json` |
| `showcase/web/xiaohongshu/search_posts` | Browser DOM crawl | ✅ Runnable | Slow-scroll keyword/tag results; `--keyword "camping" --output data/xhs_search.json` |
| `showcase/web/xiaohongshu/post_detail` | Browser DOM crawl | ✅ Runnable | Extract visible text, images, videos, engagement; `--url <URL>` |
| `showcase/app/template_click` | Desktop image template matching | ✅ Runnable | Zero AI cost; `--template assets/<system>/<button>.png` (capture your own template) |
| `showcase/android/adb_basics` | Android ADB operations | ✅ Runnable | Needs Android platform-tools / ADB; `--devices`, `--diagnostics`, `--tap-ratio 0.5 0.5` |
| `showcase/android/xiaohongshu_note` | Android ADB app flow | ✅ Runnable | Drafts a Xiaohongshu note slowly; default stops before final publish; `--profile data/xhs_profile.json --dry-run` |
| `showcase/mobile/iphone_assist` | iPhone semi-automation | ✅ Runnable | Optional `pymobiledevice3`; copy text, launch app, screenshot evidence, final steps require manual confirmation |
| `showcase/office/excel_toolkit` | File-format ops (openpyxl) | ✅ Runnable | Zero AI cost, server-friendly; `--read data.xlsx` |
| `showcase/office/ppt_generator` | File-format ops (python-pptx) | ✅ Runnable | Zero AI cost, server-friendly; `--output out.pptx --data '[...]'` |
| `showcase/office/word_report` | File-format ops (python-docx) | ✅ Runnable | Zero AI cost, server-friendly; `--output out.docx --title "Title" --data '[...]'` |
| `skills/feishu_project_daily` | Browser API interception | ✅ Runnable | Needs Chrome logged in to Feishu Project; daily schedule |

> Before running browser Skills: make sure `sh tools/start_chrome.sh` launched the RPA Chrome (not Feishu's Electron shell).

---

## FAQ

**Q: `Chrome not started with debug port` error**
Run `sh tools/start_chrome.sh` first and confirm the terminal prints the ready message. Feishu desktop also grabs port 9222 — if they conflict, quit Feishu, then start the RPA Chrome.

**Q: `Browser context management is not supported`**
Port 9222 was taken by Feishu's Electron. Run `lsof -i :9222 | grep LISTEN` to confirm which process owns it, then restart the RPA Chrome.

**Q: click_by_vision reports a vision-model error**
Set `model` in config.yaml to a multimodal model. Behind an internal AI gateway: `global.anthropic.claude-sonnet-4-6`; direct Anthropic access: `claude-sonnet-4-6`.

**Q: A desktop Skill can't find its element (new machine / app redesign)**
Desktop Skills locate elements via image template matching (`assets/<system>/*.png`), not hard-coded coordinates. A different machine, resolution, or app redesign can break the match — re-capture the template screenshots, and see the coordinate-system pitfalls in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Contributing / development

```bash
pip install -r requirements-dev.txt   # includes pytest / ruff
ruff check .                          # lint
pytest                                # tests (browser cases auto-skip without Chrome)
```

CI runs lint + tests on every PR.

Skills under `showcase/` are generic examples — **their main value is structural reference**: swap in your own system URLs, fields, and template images. To contribute a new Skill, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Platform support

| Platform | Status |
|---|---|
| macOS | ✅ Supported (Web + API + desktop control; needs Homebrew Python 3.12 + Screen Recording permission) |
| Windows | ✅ Primary support (incl. pywinauto native window control; scheduling via cron_helper.ps1) |
| HarmonyOS PC | ⏳ To be evaluated |

---

## License

[MIT](LICENSE)
