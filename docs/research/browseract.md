# BrowserAct Research

Research date: 2026-07-11.

## What BrowserAct Demonstrates

BrowserAct is organized around an Agent-facing runtime rather than an always-on browser agent. Its public model separates:

- an entry Skill that tells an Agent how to use the runtime;
- browser identities that hold login-related state and configuration;
- isolated task sessions that own tabs and command history; and
- a Skill Forge path that explores a task, produces a parameterized Skill, then tests and repairs it.

The important lesson for RPA-Everything is the lifecycle, not BrowserAct's particular browser implementation:

```text
runtime awareness -> bounded exploration -> reviewed Skill -> supervised proof -> reuse
```

## Verified Patterns Worth Borrowing

### 1. Agent Runtime Snapshot

BrowserAct asks an Agent to discover the available runtime before acting: version, browsers, active sessions, and safety rules. RPA-Everything's `harness/doctor` already detects the local prerequisites. The next step is an Agent-readable snapshot that also reports available Skills, attached devices, Chrome state, external-action policy, and the recommended next command.

This should be read-only and deterministic. It is not an invitation for an Agent to repair arbitrary user state.

Sources: [BrowserAct architecture](https://docs.browseract.com/), [BrowserAct Skill instructions](https://raw.githubusercontent.com/browser-act/skills/main/browser-act/SKILL.md).

### 2. Identity, Session, and Run Are Different Things

BrowserAct distinguishes a reusable browser identity from an isolated task session. RPA-Everything already records Runs and Traces, but currently does not have a first-class session descriptor.

For this project, begin with a small local session record: target type, selected browser/device, start time, target URL or app, and trace location. Do not start by importing cookies, rotating proxies, or adding stealth features. Session isolation only becomes a P1 implementation once concurrent Agent runs are a demonstrated user need.

Source: [BrowserAct concurrency and isolation](https://docs.browseract.com/agent-cli/concurrency-isolation).

### 3. Compact State for Browser Exploration

BrowserAct exposes a compact state view with interactive-element indices and change markers. This can reduce model tokens and stop a model from repeatedly guessing selectors. RPA-Everything should preserve DOM selectors as the durable execution representation, but offer an optional exploration-state view that is converted into stable selectors during solidification.

This is an exploration aid, not a replacement for the existing selector/template evidence hierarchy.

Source: [BrowserAct's Agent-oriented interaction model](https://docs.browseract.com/agent-cli/designed-for-agents).

### 4. Human Handoff Is a Valid Outcome

Login, MFA, CAPTCHA, or a real-world decision should not be reported as a generic failure. A Harness run should be able to return `needs_human_step` with a screenshot, the requested action, and a resume condition. This is more useful and safer than retrying clicks or assuming that a remote operator can take over.

BrowserAct's direct and isolated browser modes also reinforce that browser/profile access has different risk levels. RPA-Everything should continue to make the local user's currently logged-in browser the explicit, reviewable boundary.

Source: [BrowserAct browser modes](https://docs.browseract.com/agent-cli/browser-modes).

### 5. Make the Evidence Ladder Explicit During Solidification

BrowserAct's Skill Forge prefers network/API evidence, then DOM operations, then other fallbacks before producing a parameterized Skill and testing it. RPA-Everything already flags coordinate-driven traces for review. The next refinement is to store the chosen evidence level, preconditions, fallback behavior, and a minimal supervised proof in every generated manifest.

Source: [BrowserAct Skill Forge](https://docs.browseract.com/agent-cli/skill-forge), [Skill Forge instructions](https://raw.githubusercontent.com/browser-act/skills/main/browser-act-skill-forge/SKILL.md).

## Do Not Copy

- Stealth browsing, proxy rotation, anti-detection, and CAPTCHA workarounds. They conflict with the project's local, auditable, user-authorized position.
- Treating prompt-level confirmation as the only safety boundary. BrowserAct documents confirmation requirements for browser/profile actions, but RPA-Everything should continue enforcing external-action confirmation in code.
- A large multi-session browser manager before users demonstrate concurrent local Agent workflows.

Source: [BrowserAct safety guidance](https://docs.browseract.com/agent-cli/designed-for-agents).

## Recommended Order for RPA-Everything

1. After the current launch P0 work, add a read-only Agent runtime snapshot to extend `harness/doctor`.
2. Add `needs_human_step` as a structured Harness result with evidence and a safe resume instruction.
3. Enrich `solidify` manifests with an evidence level, explicit preconditions, and a supervised-run result.
4. Only then prototype compact browser exploration state. Add an identity/session model only if it solves verified multi-task interference.
