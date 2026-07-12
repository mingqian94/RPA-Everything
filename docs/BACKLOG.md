# RPA-Everything Backlog

This is the working backlog for a local-first Harness Agent: an Agent explores a repeated task once, then the result becomes a reviewed deterministic Skill. Priorities are ordered by user value and evidence, not by feature count.

## Current Milestone: Product Hunt Launch

Scheduled launch: **2026-07-22 00:01 PT** (15:01 China Standard Time).

### P0: Before Launch

- [ ] Replace the Product Hunt gallery placeholder with at least two real assets: a short end-to-end recording and a readable screenshot of the generated Skill / manifest. Do not present generated art as execution evidence.
- [ ] Cut a 30-60 second browser workflow demo: describe task -> dry-run plan -> trace -> solidified Skill -> supervised run evidence.
- [ ] Publish a tagged GitHub release with a concise changelog, supported-platform statement, and the one-command install path.
- [ ] Run a clean Windows installation check: setup, doctor, dry-run, and one local showcase. Record failures as issues rather than silently fixing them.
- [ ] Verify the macOS install path with a real user or CI-capable maintainer. Do not upgrade the support claim without evidence.
- [ ] Prepare launch-day copy: a GitHub release note, a short social post, and answers to expected questions about safety, reliability, LLM cost, and OS support.

### P0: Launch Day

- [ ] At 15:01 China Standard Time, verify the Product Hunt page and GitHub install link from a clean browser session.
- [ ] Respond to substantive Product Hunt comments promptly and honestly. Explain what is already deterministic, what remains supervised, and what is not supported.
- [ ] Log recurring questions, installation failures, and requested targets in GitHub issues with reproduction details.
- [ ] Do not solicit mass upvotes, create fake engagement, or make claims not backed by the repository and demos.

### P1: First 30 Days After Launch

- [ ] Convert the three most common user goals into copy-paste workflow templates and reproducible Skills.
- [ ] Turn the clean-install results into a small platform compatibility matrix: Windows, macOS, Android, iPhone assist, Linux, and HarmonyOS.
- [ ] Add an issue template for failed setup / doctor results and a feature-request template for a new automation target.
- [ ] Add one contribution-ready example that starts as an SOP, captures a trace, and lands as a reviewed Skill.
- [ ] Review Product Hunt and GitHub feedback weekly; close the loop with a public changelog entry for accepted fixes.

## Product Backlog

### P1: Trustworthy Skill Lifecycle

- [ ] Make Skill manifests easier to inspect: input assumptions, target platform, required permissions, external-action risk, and last supervised run.
- [x] Record the evidence level used by each solidified step (network/API, DOM selector, template, coordinate), its fallback, and the latest supervised proof.
- [ ] Add regression fixtures for trace solidification and redaction so a framework change cannot weaken safety boundaries unnoticed.
- [ ] Improve run history export for bug reports while keeping screenshots, URLs, and secrets opt-in and redacted by default.
- [x] Add a clear recovery path when a deterministic Skill detects UI drift: stop, capture redacted evidence, and return a repair task to the Agent.
- [x] Return `needs_human_step` for browser login/MFA, including evidence, the requested user action, and a resume condition. Extend this to other interaction types only when their detection is reliable.

### P1: Non-Developer Onboarding

- [ ] Reduce first-run configuration to a guided doctor result with precise next actions, without handling or storing user secrets in the repository.
- [x] Add a safe Agent bootstrap and no-key lifecycle preview: install dependencies, create only a template config, then inspect a bundled trace without network or external actions.
- [x] Add a read-only Agent runtime snapshot: available Skills, connected browser/device state, safety policy, and the recommended next command.
- [ ] Add a plain-language Skill review checklist before a user enables scheduling or external actions.
- [ ] Provide a minimal "first useful task" walkthrough that takes under ten minutes and has no external side effect.

### P2: Evidence and Showcase Coverage

- [ ] Add a repeatable desktop showcase that uses template matching instead of coordinates and documents the asset-maintenance cost.
- [ ] Add a browser showcase that demonstrates UI drift detection and safe refusal to continue.
- [ ] Prototype a compact browser exploration-state view; use it only to guide exploration and convert it into durable selectors during solidification.
- [ ] Add an Android evidence run that uses UI nodes and deliberately stops before final publishing.
- [ ] Keep iPhone support explicitly assistive until a reliable, reviewable remote-control path exists.

### P2: Ecosystem and Community

- [ ] Publish a short contributor guide for the full path: SOP -> trace -> Skill -> manifest -> supervised verification.
- [ ] Curate accepted community Skills by evidence quality, maintenance status, and safety boundary, not by raw quantity.
- [ ] Add an integration example for a desktop coding Agent that installs the repository Skill and calls the MCP server.

## Explicitly Deferred

- Full autonomous publishing, approval, payment, deletion, or remote-data mutation without an explicit confirmation step.
- Claiming Linux or HarmonyOS desktop automation support before a real verified target exists.
- Turning the project into a broad no-code automation platform or a hosted SaaS before the local Harness workflow is proven.
- Expanding platform count at the cost of reproducible demos, clear diagnostics, and safe recovery.

## Triage Rules

1. A P0 item blocks the current launch milestone or weakens user trust.
2. A P1 item removes repeated onboarding, maintenance, or review friction.
3. A P2 item expands demonstrated coverage after the core workflow is stable.
4. Every new item must state the user outcome, evidence required, platform assumptions, and external-action boundary before implementation begins.
