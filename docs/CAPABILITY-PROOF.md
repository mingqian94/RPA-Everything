# Capability Proof

RPA-Everything is built for a narrow outcome: an Agent explores a repeated local task once, then hands it to a reviewable deterministic Skill. This page separates what the repository can demonstrate from what it does not claim.

## The Evidence Chain

```text
User explains the work
        -> Agent plans without acting
        -> supervised exploration writes a trace
        -> trace becomes a reviewed Skill + manifest
        -> one watched run produces logs and evidence
        -> only then can the Skill be scheduled
```

Every stage has a concrete artifact: plan output, trace JSON, Python Skill, manifest, structured log, and optional screenshot/SOP evidence. Run history is available with `python run.py harness/runs -- --limit 20`.

## Verified Capability Matrix

| Path | What can be demonstrated now | Guardrail |
|---|---|---|
| Browser | Reuse a logged-in dedicated Chrome session; navigate, extract, click, type, and export a trace-derived Skill | Prefer DOM selectors; start in dry-run and protect final external actions |
| Desktop | Screenshot, input, hotkeys, and template matching on Windows/macOS | Coordinate-based trace steps remain `needs_review` until replaced with a stable template or UI selector |
| Android | ADB diagnostics, screenshots, UI-node actions, Unicode input, files, and slow draft workflows | Final publishing is off by default and needs explicit confirmation |
| iPhone | Device diagnostics, copy text, launch an app, screenshot evidence | Assistive only; no remote touch or final publishing claim |
| Office files | Deterministic Excel, PPT, and Word generation or processing | Local files only; validate outputs before sharing |

## Repeatable Demos

These scripts are recording instructions, not simulated results. Each produces evidence that a reviewer can inspect.

1. [Browser table extraction](demos/browser-table-extraction.md): public page, DOM extraction, output artifact.
2. [Android draft preparation](demos/android-draft-preparation.md): real Android device, deliberately stops before final publishing.
3. [Harness trace solidification](demos/trace-solidification.md): plan, trace JSON, generated Skill, manifest, and supervised-run boundary.

## What We Do Not Claim

- A generic Agent can safely submit, publish, approve, pay, delete, or alter remote data without an explicit human confirmation.
- A screenshot coordinate is as reliable as a browser selector or image template.
- iPhone apps can be remotely touched or published to through the current implementation.
- Linux and HarmonyOS desktop automation are exercised targets.
- Scrubbing logs is a replacement for reviewing records before sharing.

## Evaluation Standard

For every new showcase or user-contributed Skill, publish the setup assumptions, command, evidence, platform, and safety boundary. A successful first run is not enough: the flow must be understandable, reviewable, and repeatable.
