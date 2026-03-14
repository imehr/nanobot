from pathlib import Path

import pytest

from nanobot.knowledge.models import FollowUpRequest, InboxItem, IntakeDecision
from nanobot.knowledge.store import KnowledgeStore
from nanobot.knowledge.worker import KnowledgeWorker


class SuccessfulRouter:
    async def route(self, item, current_memory):
        return IntakeDecision(
            entities=["personal/bike"],
            material_type="reference",
            persistence_mode="store_facts",
        )


class FollowUpRouter:
    async def route(self, item, current_memory):
        return IntakeDecision(
            entities=["personal/bike"],
            material_type="reference",
            persistence_mode="needs_input",
            follow_up=FollowUpRequest(question="Is this personal or business?"),
        )


class FailingRouter:
    async def route(self, item, current_memory):
        raise RuntimeError("router exploded")


@pytest.mark.asyncio
async def test_worker_processes_queued_job_to_completed(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    job = store.enqueue_capture(InboxItem(content_text="Front tire pressure is 35 psi", source="telegram"))
    worker = KnowledgeWorker(tmp_path, router=SuccessfulRouter())

    processed = await worker.process_once()
    loaded = store.load_job(job.capture_id)

    assert processed is not None
    assert loaded.status == "completed"
    assert not (tmp_path / "queue" / f"{job.capture_id}.json").exists()


@pytest.mark.asyncio
async def test_worker_marks_job_needs_input_when_router_requests_follow_up(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    job = store.enqueue_capture(InboxItem(content_text="Bike invoice", source="mac_app"))
    worker = KnowledgeWorker(tmp_path, router=FollowUpRouter())

    await worker.process_once()
    loaded = store.load_job(job.capture_id)

    assert loaded.status == "needs_input"


@pytest.mark.asyncio
async def test_worker_marks_job_failed_when_router_raises(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    job = store.enqueue_capture(InboxItem(content_text="Bike insurer", source="telegram"))
    worker = KnowledgeWorker(tmp_path, router=FailingRouter())

    await worker.process_once()
    loaded = store.load_job(job.capture_id)

    assert loaded.status == "failed"
    assert "router exploded" in loaded.error
