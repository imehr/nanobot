"""Background worker for queued knowledge captures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import CaptureJob
from nanobot.knowledge.store import KnowledgeStore


class KnowledgeWorker:
    """Process queued capture jobs one at a time."""

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

    async def process_once(self) -> CaptureJob | None:
        """Claim and process the next queued job, if any."""
        jobs = self.store.list_jobs(self.store.queue_dir)
        if not jobs:
            return None

        job = self.store.transition_job(jobs[0].capture_id, status="processing")
        item = self.store.load_inbox_item(job.inbox_item_path)
        artifact_path = self._first_attachment(job.inbox_item_path)

        try:
            decision = await self.router.route(item, current_memory=self.memory.read_long_term())
            if decision.follow_up is None:
                self.store.apply_decision(decision, artifact_path=artifact_path)
                return self.store.transition_job(job.capture_id, status="completed")
            return self.store.transition_job(job.capture_id, status="needs_input")
        except Exception as exc:
            return self.store.transition_job(job.capture_id, status="failed", error=str(exc))

    def _first_attachment(self, inbox_item_path: Path) -> Path | None:
        attachments_dir = inbox_item_path / "attachments"
        if not attachments_dir.exists():
            return None
        attachments = sorted(attachments_dir.iterdir())
        return attachments[0] if attachments else None
