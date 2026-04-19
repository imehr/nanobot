#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/sync_upstream_to_fork.sh [--merge-main] [--keep-worktree] [--branch-name <name>]

Safely sync upstream/main into the imehr fork using an isolated worktree.

Options:
  --merge-main           Fast-forward local main after verification and push it to origin/codex/imehr-custom-main
  --keep-worktree        Leave the integration worktree and branch in place after success
  --branch-name <name>   Use an explicit branch name instead of a timestamped codex/upstream-sync-* branch
  --help                 Show this help text
EOF
}

log() {
  printf '[sync] %s\n' "$*"
}

fail() {
  printf '[sync] ERROR: %s\n' "$*" >&2
  exit 1
}

matches_repo() {
  local url="$1"
  local owner="$2"
  local repo="$3"

  case "$url" in
    *"/$owner/$repo"|*"/$owner/$repo.git"|*":$owner/$repo"|*":$owner/$repo.git")
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

verify_clean_tree() {
  if [[ -n "$(git -C "$REPO_ROOT" status --short)" ]]; then
    fail "Dirty working tree detected. Commit or stash changes before syncing upstream."
  fi
}

verify_remotes() {
  local origin_url upstream_url upstream_push_url
  origin_url="$(git -C "$REPO_ROOT" remote get-url origin)"
  upstream_url="$(git -C "$REPO_ROOT" remote get-url upstream)"
  upstream_push_url="$(git -C "$REPO_ROOT" remote get-url --push upstream)"

  if ! matches_repo "$origin_url" "imehr" "nanobot"; then
    fail "origin must point to imehr/nanobot. Found: $origin_url"
  fi

  if ! matches_repo "$upstream_url" "HKUDS" "nanobot"; then
    fail "upstream must point to HKUDS/nanobot. Found: $upstream_url"
  fi

  if [[ "$upstream_push_url" != "DISABLED" ]]; then
    fail "upstream push URL must be DISABLED. Found: $upstream_push_url"
  fi
}

ensure_worktree_root() {
  mkdir -p "$WORKTREE_ROOT"
  if ! git -C "$REPO_ROOT" check-ignore -q .worktrees; then
    fail ".worktrees must be ignored before running sync."
  fi
}

verify_command() {
  local pytest_bin
  pytest_bin="$(find_pytest_bin)"

  PYTHONPATH="$WORKTREE_PATH" "$pytest_bin" \
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
    tests/cli/test_commands.py \
    tests/channels/test_channel_plugins.py \
    tests/config/test_config_migration.py
}

find_pytest_bin() {
  local candidate

  for candidate in \
    "$WORKTREE_PATH/.venv/bin/pytest" \
    "$REPO_ROOT/.venv/bin/pytest" \
    "$PRIMARY_REPO_ROOT/.venv/bin/pytest"
  do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  fail "Could not find a pytest binary in the integration worktree or primary checkout."
}

cleanup() {
  if [[ "${KEEP_WORKTREE}" == "1" ]]; then
    return
  fi

  if [[ -n "${WORKTREE_PATH:-}" && -d "${WORKTREE_PATH:-}" ]]; then
    git -C "$REPO_ROOT" worktree remove "$WORKTREE_PATH" --force
  fi

  if [[ -n "${BRANCH_NAME:-}" ]]; then
    git -C "$REPO_ROOT" branch -D "$BRANCH_NAME" >/dev/null 2>&1 || true
  fi
}

MERGE_MAIN=0
KEEP_WORKTREE=0
BRANCH_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --merge-main)
      MERGE_MAIN=1
      shift
      ;;
    --keep-worktree)
      KEEP_WORKTREE=1
      shift
      ;;
    --branch-name)
      [[ $# -ge 2 ]] || fail "--branch-name requires a value"
      BRANCH_NAME="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel)"
PRIMARY_REPO_ROOT="$(dirname "$(git -C "$REPO_ROOT" rev-parse --git-common-dir)")"
WORKTREE_ROOT="$REPO_ROOT/.worktrees"
[[ -n "$BRANCH_NAME" ]] || BRANCH_NAME="codex/upstream-sync-$(date +%Y%m%d-%H%M%S)"
[[ "$BRANCH_NAME" == codex/* ]] || fail "Branch name must start with codex/"
WORKTREE_PATH="$WORKTREE_ROOT/${BRANCH_NAME//\//-}"

trap cleanup EXIT

log "Validating remotes"
verify_remotes

log "Checking repo state"
verify_clean_tree
ensure_worktree_root

log "Creating isolated worktree at $WORKTREE_PATH"
git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME"

log "Fetching upstream"
git -C "$WORKTREE_PATH" fetch upstream --prune

log "Merging upstream/main into $BRANCH_NAME"
git -C "$WORKTREE_PATH" merge --no-edit upstream/main

log "Running verification slice"
verify_command
log "Verification passed"

log "Pushing integration branch to origin"
git -C "$WORKTREE_PATH" push -u origin "$BRANCH_NAME"
log "Pushed integration branch to origin"

if [[ "$MERGE_MAIN" == "1" ]]; then
  log "Fast-forwarding local main"
  git -C "$REPO_ROOT" merge --ff-only "$BRANCH_NAME"
  git -C "$REPO_ROOT" push origin main:codex/imehr-custom-main
  log "Updated local main and pushed origin/codex/imehr-custom-main"
fi

if [[ "$KEEP_WORKTREE" == "1" ]]; then
  log "Keeping worktree at $WORKTREE_PATH"
fi
