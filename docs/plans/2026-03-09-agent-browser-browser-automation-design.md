# Agent Browser For Browser Automation Design

**Date:** 2026-03-09

**Goal**

Replace MCP only for browser automation tasks in `nanobot` with a native `agent-browser` integration, while keeping non-browser MCP support unchanged and preserving the existing `smaug` X bookmarks ingestion flow.

**Current State**

- `nanobot` supports external tools through generic MCP server registration.
- Browser automation is not a first-class native tool in `nanobot`.
- `smaug` fetches X bookmarks through the `bird` CLI and local X session cookies, not through `nanobot` MCP browser automation.
- `smaug` processing invokes Claude Code or OpenCode after fetch, but bookmark retrieval itself is independent from the MCP integration in `nanobot`.

**Problem**

Using MCP for browser automation adds an extra abstraction layer where the desired standard is now `vercel-labs/agent-browser`. The system needs a browser path that:

- does not depend on MCP for browser tasks,
- remains compatible with Claude Code style browser operations,
- works cleanly with `nanobot` session-based automations,
- does not break `smaug` bookmark extraction or related X workflows.

## Requirements

### Functional

- `nanobot` must expose browser automation as a native tool backed by `agent-browser`.
- Non-browser MCP support must remain unchanged.
- The browser tool must support common actions needed by agent workflows:
  - open/navigate
  - snapshot/inspect page state
  - click
  - fill/type
  - extract text or structured values
  - screenshot
  - close/end session
- Browser sessions should be reusable across multiple turns in the same `nanobot` conversation.
- The integration must support authenticated browser workflows, especially X-related tasks.

### Compatibility

- Claude Code style workflows should still be able to drive browser tasks through `nanobot`.
- `smaug` bookmark fetch must continue to work through `bird` with no forced migration.
- If `nanobot` orchestrates browser steps around X or other authenticated sites, it should be able to use `agent-browser` without MCP.

### Operational

- If `agent-browser` is not installed or not configured correctly, the failure mode must be explicit and actionable.
- The integration should avoid requiring a persistent background daemon unless `agent-browser` itself requires it.
- Session naming must be deterministic enough to avoid collisions across concurrent `nanobot` conversations.

## Proposed Architecture

### 1. Add a native `agent_browser` tool

Create a new native tool in `nanobot` that shells out to the `agent-browser` CLI and translates its JSON responses into ordinary tool results. This tool becomes the only supported path for browser automation inside `nanobot`.

This keeps the browser pathway explicit and makes it independent from the MCP client lifecycle.

### 2. Keep MCP untouched for non-browser tools

No changes to the generic MCP transport, connection model, or existing non-browser MCP configuration are required for this feature.

The only behavioral change is documentation and runtime guidance: browser automation should use `agent-browser`, not an MCP browser server.

### 3. Session-aware browser execution

Each `nanobot` conversation/session should map to a stable `agent-browser` session identifier. That allows:

- login state reuse,
- multi-step browser tasks over several turns,
- automation runs that interact with the same browser context,
- easier debugging for long-running workflows.

Recommended session format:

- `nanobot-<channel>-<chat-id>-<session-key>`

This should be sanitized for CLI safety and length-limited if needed.

### 4. Config-driven browser runtime

Add a dedicated browser tool config section to `nanobot` rather than overloading `mcp_servers`.

Recommended config fields:

- `enabled`
- `command` or executable path
- `headless`
- `cdp_url` or equivalent Chrome attach setting if supported
- `timeout`
- `extra_args`

This makes browser automation a first-class capability instead of an external tool-server pattern.

## Tool Surface

The native browser tool should expose a small, durable action schema instead of mirroring every raw CLI command one-to-one.

Recommended high-level actions:

- `open`
  - input: `url`, optional session options
- `snapshot`
  - input: optional selector/scope
- `click`
  - input: target reference, selector, or text hint
- `fill`
  - input: target plus value
- `extract`
  - input: selector/query and output mode
- `screenshot`
  - input: optional path or scope
- `close`
  - input: optional session

Where `agent-browser` provides element references from snapshots, the tool should preserve those references in the returned text so the model can act on them in subsequent calls.

## Smaug Impact

### What should not change

- `smaug` should continue using `bird` to fetch X bookmarks.
- `smaug` should continue using its current cookie extraction workflow unless there is a separate need to modernize it.
- The `.claude` bookmark processing command does not need to be rewritten for this feature.

### What may benefit later

If `nanobot` is orchestrating X-related browser workflows outside `bird`, those flows can use the new native `agent_browser` tool with:

- a persistent browser session, or
- an attached signed-in Chrome instance if `agent-browser` supports that mode reliably.

This keeps `smaug` bookmark ingestion stable while enabling future browser-driven automations in the same ecosystem.

## Failure Handling

The browser tool should return explicit tool errors for:

- missing executable,
- malformed JSON from CLI,
- session startup failures,
- navigation timeouts,
- unsupported actions,
- browser already closed or missing session state.

Error messages should tell the operator what to fix, for example:

- install `agent-browser`,
- configure the executable path,
- retry with a fresh session,
- attach to a signed-in browser profile.

## Testing Strategy

### Unit tests

- config parsing for browser settings,
- session name derivation from conversation context,
- CLI argument construction per action,
- result parsing and error handling,
- unavailable-binary behavior.

### Integration tests

- run against a static local page or lightweight fixture:
  - open page,
  - snapshot,
  - click,
  - fill,
  - extract text,
  - close session.

### Manual verification

- verify non-browser MCP still loads and functions,
- verify `nanobot` can perform a browser task through the new native tool,
- verify `smaug` bookmark fetch still works unchanged,
- verify an authenticated X-adjacent flow can reuse browser state when configured.

## Rollout Plan

1. Add browser config schema and defaults.
2. Add native `agent_browser` tool implementation.
3. Register the tool in the main agent loop.
4. Add tests for tool invocation, config, and failure cases.
5. Update README to state:
   - browser automation uses `agent-browser`,
   - MCP remains available for non-browser tools.
6. Add compatibility notes for `smaug` and X workflows.

## Decisions

- Browser automation in `nanobot` will no longer rely on MCP.
- Non-browser MCP support stays in place.
- `smaug` bookmark fetching remains on `bird`.
- The replacement should be native, session-aware, and explicit in config and docs.

## Out Of Scope

- Removing all MCP support from `nanobot`.
- Rewriting `smaug` bookmark ingestion away from `bird`.
- Replacing `smaug` cookie extraction unless required by a separate issue.
- Broad automation redesign across Claude Code, OpenCode, and `smaug`.
