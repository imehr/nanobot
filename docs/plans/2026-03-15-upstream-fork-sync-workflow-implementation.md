# Upstream Fork Sync Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add durable repo-local instructions and a safe reusable upstream-sync script for the `imehr` fork without ever pushing to upstream.

**Architecture:** Store the operating policy in root `AGENTS.md` so repo-aware agents see it immediately, and implement the actual sync mechanics in one shell script under `scripts/`. The script validates remotes, works in a temporary `.worktrees/` branch, runs a verification slice, and only updates the fork/local main when explicitly requested.

**Tech Stack:** Markdown, Bash, git, pytest

---

### Task 1: Add repo-local agent instructions

**Files:**
- Create: `AGENTS.md`
- Inspect: `workspace/AGENTS.md`

**Step 1: Write the root agent instructions**

Include:
- repo identity and fork model
- `origin` and `upstream` rules
- explicit “never push to upstream”
- worktree requirement for upstream sync
- local runtime paths and app paths
- verification slice command
- cleanup expectations

**Step 2: Review for brevity and operational clarity**

Confirm the file is short enough that an agent can use it directly without reading extra docs.

**Step 3: Stage but do not commit yet**

### Task 2: Add the sync script

**Files:**
- Create: `scripts/sync_upstream_to_fork.sh`

**Step 1: Write the failing behavior checklist**

The script must:
- fail on dirty repo
- fail if `origin` is not `imehr/nanobot`
- fail if `upstream` is not `HKUDS/nanobot`
- fail if `upstream` push URL is not `DISABLED`
- create a timestamped `codex/` worktree branch
- fetch and merge `upstream/main`
- run the verification slice
- push the integration branch to `origin`
- optionally fast-forward local `main` and push to `origin/codex/imehr-custom-main`
- clean up the worktree and local branch

**Step 2: Implement the minimal script**

Add:
- strict shell flags
- argument parsing for:
  - `--merge-main`
  - `--keep-worktree`
  - `--branch-name <name>` optional
- clear logging for each stage

**Step 3: Make the script executable**

Run:
```bash
chmod +x scripts/sync_upstream_to_fork.sh
```

### Task 3: Document the verification slice inside the script

**Files:**
- Modify: `scripts/sync_upstream_to_fork.sh`

**Step 1: Add the verification command exactly**

Use:
```bash
PYTHONPATH="$REPO_ROOT" "$REPO_ROOT/.venv/bin/pytest" \
  tests/test_knowledge_config.py \
  tests/test_knowledge_store.py \
  tests/test_knowledge_router.py \
  tests/test_knowledge_service.py \
  tests/test_knowledge_queue.py \
  tests/test_knowledge_retract.py \
  tests/test_knowledge_worker.py \
  tests/test_knowledge_native_inbox.py \
  tests/test_knowledge_native_status.py \
  tests/test_knowledge_web_inbox.py \
  tests/test_knowledge_watcher.py \
  tests/test_memory_context.py \
  tests/test_project_memory_router.py \
  tests/test_project_memory_store.py \
  tests/test_project_memory_worker.py \
  tests/test_capture_mode.py \
  tests/test_voice_channel.py \
  tests/test_agent_browser_tool.py \
  tests/test_commands.py \
  tests/test_channel_plugins.py \
  tests/test_config_migration.py
```

**Step 2: Make the script stop immediately if verification fails**

### Task 4: Add a short pointer in the README

**Files:**
- Modify: `README.md`

**Step 1: Add a short local-fork maintenance note**

Keep it short. Mention:
- this checkout is maintained as a customized fork
- use `scripts/sync_upstream_to_fork.sh` for upstream sync
- upstream is fetch-only here

### Task 5: Verify the workflow locally

**Files:**
- Inspect only

**Step 1: Verify root repo is clean before test run**

Run:
```bash
git status --short
```

Expected: no output

**Step 2: Run the sync script in a safe validation mode**

Run:
```bash
scripts/sync_upstream_to_fork.sh --keep-worktree
```

Expected:
- remote validation passes
- worktree is created
- merge and verification run
- integration branch is pushed to `origin`
- worktree remains for inspection because of `--keep-worktree`

**Step 3: Clean up the kept worktree manually**

Run:
```bash
git worktree list
git worktree remove <path>
git branch -D <branch>
```

### Task 6: Commit the workflow

**Step 1: Commit**

```bash
git add AGENTS.md README.md scripts/sync_upstream_to_fork.sh \
  docs/plans/2026-03-15-upstream-fork-sync-workflow-design.md \
  docs/plans/2026-03-15-upstream-fork-sync-workflow-implementation.md
git commit -m "chore: add fork sync workflow"
```
