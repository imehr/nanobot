"""Workspace-backed knowledge storage helpers."""

from __future__ import annotations

from pathlib import Path

from nanobot.config.schema import KnowledgeConfig


class KnowledgeStore:
    """Create and manage the hybrid knowledge workspace layout."""

    def __init__(
        self,
        workspace: Path,
        config: KnowledgeConfig | None = None,
    ) -> None:
        self.workspace = workspace
        self.config = config or KnowledgeConfig()

    @property
    def inbox_dir(self) -> Path:
        return self.workspace / self.config.inbox_dir

    @property
    def entities_dir(self) -> Path:
        return self.workspace / self.config.entities_dir

    @property
    def ledgers_dir(self) -> Path:
        return self.workspace / self.config.ledgers_dir

    @property
    def indexes_dir(self) -> Path:
        return self.workspace / self.config.indexes_dir

    @property
    def review_dir(self) -> Path:
        return self.workspace / self.config.review_dir

    def bootstrap(self) -> None:
        """Create the knowledge workspace directories if they do not exist."""
        for path in (
            self.inbox_dir,
            self.entities_dir,
            self.ledgers_dir,
            self.indexes_dir,
            self.review_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
