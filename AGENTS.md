# Agent Instructions

This repository is a customized fork for `imehr`, built on top of upstream `HKUDS/nanobot`.

## Repo Identity

- Treat this checkout as the writable source of truth for `imehr` only.
- Keep upstream changes flowing in, but never treat upstream as a push target.
- Preserve local customizations around capture, Mehr memory, native macOS tooling, and project memory.

## Remote Safety

- `origin` must point to `imehr/nanobot`.
- `upstream` must point to `HKUDS/nanobot`.
- `upstream` is fetch-only here. Never push to it.
- `git remote get-url --push upstream` must stay `DISABLED`.

## Default Upstream Sync Workflow

- Do not run ad hoc upstream merges in the main checkout.
- Use `scripts/sync_upstream_to_fork.sh` as the default sync path.
- The script creates an isolated `.worktrees/` branch, merges `upstream/main`, runs verification, pushes only to your fork, and optionally fast-forwards local `main`.
- Use `--merge-main` only after verification succeeds and you want local `main` updated as well.

## Branching And Cleanup

- Use `codex/` branches for feature work, sync work, and risky changes.
- Prefer `.worktrees/` for isolated implementation work.
- Keep local `main` clean when work is done.
- Remove temporary worktrees after successful integration unless you are actively debugging a failure.

## Local Runtime Setup

- Canonical memory: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr`
- Archive root: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive`
- Drop folder: `/Users/mehranmozaffari/Drop to Nanobot`
- Native capture health: `http://127.0.0.1:18792/health`
- Local web inbox: `http://127.0.0.1:18791/`
- Installed app: `/Applications/NanobotCapture.app`

## Verification Policy

Before claiming an upstream integration is ready, run this verification slice from the integration worktree:

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

## Notes For Claude Code And Similar Agents

- Read this file first before making git or workflow decisions.
- Prefer the scripted workflow over custom git sequences.
- If upstream sync is requested, validate remotes first and keep all pushes on `origin` only.
