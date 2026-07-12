# Firecrawl Keyless Research

Research date: 2026-07-12.

## What Keyless Demonstrates

Firecrawl Keyless removes the first integration hurdle for public-web work: an
Agent can use Firecrawl's hosted MCP endpoint, CLI, or SDK without first
creating and pasting an API key. The product lesson is not "free crawling";
it is a staged adoption model:

```text
zero-config, read-only first result
    -> visible limits and status
    -> explicit account / key / permission upgrade
    -> broader capability or production use
```

The current official rate-limit documentation says keyless requests must come
from an official Firecrawl client and are limited to `scrape`, `search`,
`interact`, and `parse`; `crawl`, `map`, `extract`, batch operations, and the
other endpoints require a key. It is rate-limited per IP with separate daily
request and credit caps. The launch post describes 1,000 monthly credits, but
the current rate-limit page describes 1,000 free credits after sign-up and does
not publish a numeric keyless quota. Do not make an implementation depend on a
specific keyless allowance.

Sources: [Keyless launch post](https://www.firecrawl.dev/blog/firecrawl-keyless-launch),
[rate limits](https://docs.firecrawl.dev/rate-limits),
[MCP server documentation](https://docs.firecrawl.dev/mcp-server).

## Product Mechanics Worth Noting

### 1. Direct Agent Integration, Not Screen Automation

The keyless MCP endpoint is a remote URL (`https://mcp.firecrawl.dev/v2/mcp`)
that can be connected without an API key. It exposes structured web operations
such as search and scrape rather than asking the Agent to find screen
coordinates. A configured API key raises limits and enables the complete tool
set.

This is the same control-channel distinction RPA-Everything should keep:

```text
MCP / CLI / API -> DOM / accessibility tree -> template / UI node -> vision
```

The first available path should be selected; visual recognition is a last
resort, not an equal alternative.

Sources: [MCP server documentation](https://docs.firecrawl.dev/mcp-server),
[Firecrawl CLI](https://github.com/firecrawl/cli).

### 2. The Free Path Is Deliberately Narrow

Keyless does not mean anonymous, unlimited, or local. Firecrawl documents the
hosted keyless MCP as rate-limited per IP and narrower than a local MCP server.
For example, hosted MCP cannot read local files directly; local file handling
requires a handoff/upload flow. Firecrawl also documents that its CLI can
collect anonymous usage telemetry, with an opt-out environment variable.

For RPA-Everything, every future no-config route must disclose the same facts:

- whether it uses a remote service;
- what data leaves the machine;
- the quota, timeout, and failure behavior; and
- the exact condition that requires a user-configured credential.

Sources: [hosted vs local MCP](https://docs.firecrawl.dev/mcp-server),
[Firecrawl CLI telemetry](https://github.com/firecrawl/cli).

### 3. Status and Limits Are First-Class Agent Inputs

The Firecrawl CLI exposes status, authentication, concurrency, and credit
information. Its asynchronous operations also expose job status, cancellation,
timeouts, and maximum-credit controls. This makes constrained resources
visible before an Agent spends them.

RPA-Everything already has `harness/runtime` for readiness and safety. The
missing extension is a uniform status contract for an optional direct
integration: installed, authenticated, online/offline, read-only or
external-action risk, quota/budget if known, and the local fallback.

Sources: [Firecrawl CLI](https://github.com/firecrawl/cli),
[MCP server documentation](https://docs.firecrawl.dev/mcp-server).

## What RPA-Everything Should Borrow

### 1. A No-Key, No-Side-Effect First Success Path

Do not promise a Keyless Harness: planning still needs the user's chosen LLM
provider. Instead, provide a built-in, deterministic first-run demonstration
that requires neither an LLM key nor an external action. It should show the
Lifecycle with a bundled trace:

```text
doctor -> runtime -> replay --dry-run -> inspect evidence/manifest
```

User outcome: a non-developer verifies that the framework installed and can
explain a Skill before configuring a model or connecting an account.

Evidence required: clean Windows run with no network credential and no remote
mutation. Platform: Windows first, then macOS. Safety boundary: the demo may
read bundled files only.

### 2. Direct Integrations Need an Explicit Contract

Build on `showcase/app/integration/`, but do not add a generic arbitrary-command
runner. Each concrete integration should declare:

- required local executable or MCP endpoint;
- credential state without exposing the credential;
- remote-data boundary and any telemetry;
- read-only versus external-action operations;
- quota/timeout/budget behavior; and
- deterministic fallback, normally to DOM/UI only when the user accepts it.

Expose those declarations in `harness/runtime` before the planner can choose a
direct Skill. An unavailable direct route should be reported, not silently
replaced with visual clicking.

### 3. Make Route Choice Reviewable

The Harness prompt already says to prefer `app/integration/` when a registered
direct Skill exists. The next improvement is to include the selected evidence
route and rejected alternatives in the plan/trace:

```text
selected: direct MCP/CLI/API
fallback: browser DOM selector
vision: forbidden unless prior routes are unavailable and the user approves
```

That makes the Agent's choice inspectable and prevents a convenient cloud
connector from hiding a local-data or cost trade-off.

### 4. Add a Resource Boundary to Optional Integrations

For integrations with metered requests or long-running jobs, standardize
`--status`, `--timeout`, and a capped budget/limit flag where the provider
supports one. Report `needs_human_step` or a structured limit result instead
of retrying until an allowance is exhausted.

## What Not To Copy

- Do not treat a cloud keyless endpoint as local or private. RPA-Everything is
  local-first; private URLs, login cookies, customer data, and local documents
  must not be sent to a third-party service by a default path.
- Do not add remote profile persistence, stealth behavior, proxy rotation, or
  unattended cloud browser sessions. Those conflict with the project's
  auditable, user-authorized browser boundary.
- Do not allow a direct integration to bypass `--confirm-external` for send,
  publish, approve, pay, delete, or remote-data mutation.
- Do not advertise a fixed free quota. Provider limits can change and must be
  discovered at runtime or documented as provider-controlled.

## Recommended Order

1. After launch P0 work, add the bundled no-key lifecycle demonstration.
2. Define and display the direct-integration status contract in
   `harness/runtime`.
3. Add one real, user-demanded read-only MCP/CLI integration as the reference
   implementation, including timeout/limit reporting and a no-secret test.
4. Only after that, record route selection and fallback evidence in plans and
   traces.

Do not make Firecrawl Keyless itself a default dependency. It may be a future
optional `app/integration` example for public, read-only web research, but it
is a hosted third-party service and requires a user-visible remote-data
consent boundary.
