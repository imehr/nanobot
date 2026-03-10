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
    """Result returned after capturing and routing an item."""

    inbox_item_path: Path
    entities: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    follow_up: FollowUpRequest | None = None


class KnowledgeIntakeService:
    """Store raw capture items, route them, and apply canonical writes."""

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
        inbox_item_path = self.store.save_inbox_item(item)
        decision = await self.router.route(item, current_memory=self.memory.read_long_term())
        actions = ["saved original"]
        if decision.follow_up is None:
            self.store.apply_decision(decision)
            actions.append("applied decision")
        return CaptureResult(
            inbox_item_path=inbox_item_path,
            entities=decision.entities,
            actions=actions,
            follow_up=decision.follow_up,
        )

    async def capture_file(self, file_path: Path, *, user_hint: str = "", source: str = "local") -> CaptureResult:
        item = InboxItem(
            content_text=f"Uploaded file: {file_path.name}",
            user_hint=user_hint,
            source=source,
            capture_type="file",
        )
        inbox_item_path = self.store.save_inbox_item(item)
        self.store.attach_file(inbox_item_path, file_path)
        decision = await self.router.route(item, current_memory=self.memory.read_long_term())
        actions = ["saved original"]
        if decision.follow_up is None:
            self.store.apply_decision(decision, artifact_path=file_path)
            actions.append("applied decision")
        return CaptureResult(
            inbox_item_path=inbox_item_path,
            entities=decision.entities,
            actions=actions,
            follow_up=decision.follow_up,
        )
