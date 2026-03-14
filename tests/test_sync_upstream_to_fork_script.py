from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_upstream_to_fork.sh"


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=cwd)


def init_bare_repo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", str(path)], check=True, capture_output=True, text=True)


def clone_repo(origin: Path, checkout: Path) -> None:
    subprocess.run(["git", "clone", str(origin), str(checkout)], check=True, capture_output=True, text=True)


def write_file(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", ".")
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def prepare_repo(tmp_path: Path) -> Path:
    origin = tmp_path / "imehr" / "nanobot.git"
    upstream = tmp_path / "HKUDS" / "nanobot.git"
    init_bare_repo(origin)
    init_bare_repo(upstream)

    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-b", "main")
    git(seed, "config", "user.name", "Seed User")
    git(seed, "config", "user.email", "seed@example.com")
    write_file(seed / "README.md", "seed\n")
    commit_all(seed, "seed commit")
    git(seed, "remote", "add", "origin", str(origin))
    git(seed, "push", "-u", "origin", "main")
    git(seed, "remote", "set-url", "upstream", str(upstream))
    git(seed, "push", str(upstream), "main")

    checkout = tmp_path / "checkout"
    clone_repo(origin, checkout)
    git(checkout, "checkout", "-b", "main", "origin/main")
    git(checkout, "remote", "add", "upstream", str(upstream))
    git(checkout, "remote", "set-url", "--push", "upstream", "DISABLED")
    git(checkout, "config", "user.name", "Test User")
    git(checkout, "config", "user.email", "test@example.com")
    write_file(checkout / ".gitignore", ".worktrees/\n")
    write_file(checkout / ".venv" / "bin" / "pytest", "#!/bin/sh\nexit 0\n", executable=True)
    write_file(checkout / "README.md", "checkout\n")
    write_file(checkout / "workspace" / "AGENTS.md", "# Workspace\n")
    for test_name in (
        "test_knowledge_config.py",
        "test_knowledge_store.py",
        "test_knowledge_router.py",
        "test_knowledge_service.py",
        "test_knowledge_queue.py",
        "test_knowledge_retract.py",
        "test_knowledge_worker.py",
        "test_knowledge_native_inbox.py",
        "test_knowledge_native_status.py",
        "test_knowledge_web_inbox.py",
        "test_knowledge_watcher.py",
        "test_memory_context.py",
        "test_project_memory_router.py",
        "test_project_memory_store.py",
        "test_project_memory_worker.py",
        "test_capture_mode.py",
        "test_voice_channel.py",
        "test_agent_browser_tool.py",
        "test_commands.py",
        "test_channel_plugins.py",
        "test_config_migration.py",
    ):
        write_file(checkout / "tests" / test_name, "def test_placeholder():\n    assert True\n")
    commit_all(checkout, "local setup")
    git(checkout, "push", "origin", "main")

    upstream_work = tmp_path / "upstream-work"
    clone_repo(upstream, upstream_work)
    git(upstream_work, "checkout", "-b", "main", "origin/main")
    git(upstream_work, "config", "user.name", "Upstream User")
    git(upstream_work, "config", "user.email", "upstream@example.com")
    write_file(upstream_work / "UPSTREAM_CHANGE.md", "upstream change\n")
    commit_all(upstream_work, "upstream change")
    git(upstream_work, "push", "origin", "main")

    script_target = checkout / "scripts" / "sync_upstream_to_fork.sh"
    script_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT_PATH, script_target)
    script_target.chmod(0o755)
    commit_all(checkout, "add sync script")
    git(checkout, "push", "origin", "main")
    return checkout


def test_script_fails_in_dirty_repo(tmp_path: Path) -> None:
    repo = prepare_repo(tmp_path)
    write_file(repo / "DIRTY.txt", "dirty\n")

    result = run(["./scripts/sync_upstream_to_fork.sh"], cwd=repo)

    assert result.returncode != 0
    assert "dirty working tree" in (result.stderr + result.stdout).lower()


def test_script_rejects_non_imehr_origin(tmp_path: Path) -> None:
    repo = prepare_repo(tmp_path)
    git(repo, "remote", "set-url", "origin", str(tmp_path / "someone-else" / "nanobot.git"))

    result = run(["./scripts/sync_upstream_to_fork.sh"], cwd=repo)

    assert result.returncode != 0
    assert "origin must point to imehr/nanobot" in (result.stderr + result.stdout).lower()


def test_script_syncs_upstream_branch_and_keeps_worktree_when_requested(tmp_path: Path) -> None:
    repo = prepare_repo(tmp_path)

    result = run(
        [
            "./scripts/sync_upstream_to_fork.sh",
            "--keep-worktree",
            "--branch-name",
            "codex/test-sync",
        ],
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    kept_path = repo / ".worktrees" / "codex-test-sync"
    assert kept_path.exists()
    assert "verification passed" in (result.stderr + result.stdout).lower()
    assert "pushed integration branch to origin" in (result.stderr + result.stdout).lower()

    origin_refs = git(repo, "ls-remote", "--heads", "origin", "codex/test-sync")
    assert "codex/test-sync" in origin_refs.stdout
