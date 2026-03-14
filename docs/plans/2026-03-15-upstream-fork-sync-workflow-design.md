# Upstream Fork Sync Workflow Design

**Goal:** Preserve the fork-only workflow for `imehr/nanobot`, make it obvious to coding agents how this repo is meant to be maintained, and provide one safe path for upstream syncs that never pushes to `HKUDS/nanobot`.

## Problem

This repo now has two identities:

- it is based on upstream `HKUDS/nanobot`
- it is also a heavily customized local/forked build with capture, Mehr memory, native macOS tooling, and local operational conventions

Without an explicit repo-local memory layer, future coding agents may:

- push to the wrong remote
- treat upstream as the writable source of truth
- skip the worktree-based integration process
- lose or overwrite local customizations
- leave `main` dirty after partial sync work

The repo needs a durable, agent-readable policy plus a repeatable sync command.

## Recommended Approach

Use two layers:

1. Root `AGENTS.md`
   - Canonical operating instructions for Claude Code, Codex, and similar repo-aware agents.
   - Explains the fork/upstream relationship, remote safety rules, worktree requirement, verification policy, and cleanup expectations.

2. `scripts/sync_upstream_to_fork.sh`
   - The default operational path for upstream integration.
   - Fetches upstream, creates a temporary `codex/` worktree branch, merges `upstream/main`, runs a defined verification slice, and pushes only to the `imehr` fork.
   - Supports an explicit option to fast-forward local `main` only after verification.

This keeps the policy human-readable and the risky workflow scripted.

## Repo Memory Design

Root `AGENTS.md` should answer these questions immediately:

- What repo is this?
- Which remote is safe to push to?
- Which remote is fetch-only?
- How should upstream integration be done?
- What local runtime setup matters for this fork?
- What verification must be run before claiming sync success?
- What cleanup is required after integration?

The file should be short and operational, not a long historical document.

It should include:

- `origin` must remain `imehr/nanobot`
- `upstream` must remain `HKUDS/nanobot` and must never be pushed to
- `upstream` push URL should stay disabled
- use isolated worktrees for upstream merges and risky feature work
- keep local `main` clean
- default upstream sync method is the provided script
- important local paths and services:
  - `~/Library/Mobile Documents/com~apple~CloudDocs/Mehr`
  - `~/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive`
  - `~/Drop to Nanobot`
  - native capture endpoint
  - local web inbox
  - installed `NanobotCapture.app`

## Sync Script Design

Recommended script path:

- `scripts/sync_upstream_to_fork.sh`

Recommended behavior:

1. Validate git remotes
   - `origin` must point at `imehr/nanobot`
   - `upstream` must point at `HKUDS/nanobot`
   - `upstream` push URL must be `DISABLED`

2. Validate repo state
   - refuse to run if the current checkout is dirty
   - ensure `.worktrees/` exists and is ignored

3. Create isolated integration branch/worktree
   - branch name like `codex/upstream-sync-YYYYMMDD-HHMMSS`

4. Fetch and merge
   - fetch `upstream --prune`
   - merge `upstream/main` into the worktree branch

5. Run verification
   - use the agreed custom verification slice that covers:
     - knowledge queue/memory
     - capture mode
     - native inbox/web inbox
     - project memory
     - voice channel
     - browser tool
     - commands
     - plugin config
     - config migration

6. Push to fork only
   - push branch to `origin`

7. Optional local main update
   - if explicitly requested via flag, fast-forward local `main` to the verified branch
   - push local `main` to `origin/codex/imehr-custom-main`

8. Cleanup
   - remove worktree
   - delete local temporary branch

## Safety Rules

- Never push to `upstream`
- Never merge directly in a dirty working tree
- Never skip verification before updating local `main`
- Never overwrite fork tracking accidentally by pushing to `origin/main`
- Always push the maintained local branch to `origin/codex/imehr-custom-main`

## Testing

The script should be covered with focused shell-level tests or a Python test harness only if the repo already has a suitable pattern. Otherwise:

- keep the script simple and deterministic
- rely on integration-safe command structure
- verify with a documented dry-run mode and manual command validation

## Recommendation

Implement:

- root `AGENTS.md`
- `scripts/sync_upstream_to_fork.sh`
- documentation in `README.md` pointing to the workflow

YAGNI:

- do not build a complex sync daemon
- do not automate conflict resolution
- do not auto-push to any upstream/default branch
