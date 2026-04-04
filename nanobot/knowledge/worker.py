"""Background worker for queued knowledge captures."""

from __future__ import annotations

import asyncio
import threading
import time
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
            decision = await self.router.route(item, current_memory=self.memory.read_memory())
            if decision.follow_up is None:
                canonical_paths, archive_paths = self.store.apply_decision(
                    decision,
                    artifact_path=artifact_path,
                    capture_id=job.capture_id,
                )
                project_memory_paths = self.store.apply_project_memory_actions(
                    decision.project_name,
                    decision.project_memory_actions,
                )
                return self.store.transition_job(
                    job.capture_id,
                    status="completed",
                    canonical_paths=canonical_paths,
                    archive_paths=archive_paths,
                    project_memory_paths=project_memory_paths,
                )
            return self.store.transition_job(
                job.capture_id,
                status="needs_input",
                follow_up=decision.follow_up.question,
            )
        except Exception as exc:
            return self.store.transition_job(job.capture_id, status="failed", error=str(exc))

    def _first_attachment(self, inbox_item_path: Path) -> Path | None:
        attachments_dir = inbox_item_path / "attachments"
        if not attachments_dir.exists():
            return None
        attachments = sorted(attachments_dir.iterdir())
        return attachments[0] if attachments else None


class KnowledgeWorkerService:
    """Background polling service that processes queued jobs."""

    def __init__(self, worker: KnowledgeWorker, *, poll_interval_seconds: float = 0.5) -> None:
        self.worker = worker
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            asyncio.run(self.worker.process_once())
            time.sleep(self.poll_interval_seconds)
