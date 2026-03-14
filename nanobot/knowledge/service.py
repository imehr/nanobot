"""High-level capture service for hybrid knowledge intake."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import FollowUpRequest, InboxItem
from nanobot.knowledge.router import KnowledgeRouter
from nanobot.knowledge.store import KnowledgeStore


@dataclass
class CaptureResult:
    """Result returned after staging and queueing an item."""

    capture_id: str
    status: str
    inbox_item_path: Path
    entities: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    project_memory_paths: list[Path] = field(default_factory=list)
    follow_up: FollowUpRequest | None = None


class KnowledgeIntakeService:
    """Stage raw capture items locally and enqueue them for background processing."""

    def __init__(
        self,
        workspace: Path,
        *,
        router: Any,
        config: KnowledgeConfig | None = None,
    ) -> None:
        self.workspace = workspace
        self.config = config or KnowledgeConfig()
        self.store = KnowledgeStore(workspace, self.config)
        self.router = router
        self.memory = MemoryStore(workspace)

    @classmethod
    def for_testing(cls, workspace: Path, *, router: Any) -> "KnowledgeIntakeService":
        return cls(workspace, router=router)

    async def capture_text(self, content_text: str, *, user_hint: str = "", source: str = "local") -> CaptureResult:
        item = InboxItem(content_text=content_text, user_hint=user_hint, source=source, capture_type="text")
        job = self.store.enqueue_capture(item)
        return CaptureResult(
            capture_id=job.capture_id,
            status=job.status,
            inbox_item_path=job.inbox_item_path,
            actions=["saved original", "queued"],
        )

    async def capture_file(
        self,
        file_path: Path,
        *,
        user_hint: str = "",
        source: str = "local",
        content_text: str = "",
    ) -> CaptureResult:
        item = InboxItem(
            content_text=content_text or f"Uploaded file: {file_path.name}",
            user_hint=user_hint,
            source=source,
            capture_type="file",
        )
        job = self.store.enqueue_capture(item)
        self.store.attach_file(job.inbox_item_path, file_path)
        return CaptureResult(
            capture_id=job.capture_id,
            status=job.status,
            inbox_item_path=job.inbox_item_path,
            actions=["saved original", "queued"],
        )

    def retract_capture(self, capture_id: str) -> CaptureResult:
        """Retract a processed capture and remove its linked outputs."""
        job = self.store.retract_job(capture_id)
        return CaptureResult(
            capture_id=job.capture_id,
            status=job.status,
            inbox_item_path=job.inbox_item_path,
            actions=["retracted"],
        )
