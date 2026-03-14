from pathlib import Path

import pytest

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import InboxItem, IntakeDecision
from nanobot.knowledge.service import KnowledgeIntakeService
from nanobot.knowledge.store import KnowledgeStore
from nanobot.knowledge.worker import KnowledgeWorker


class KeepOriginalRouter:
    async def route(self, item, current_memory):
        return IntakeDecision(
            entities=["personal/bike"],
            material_type="document",
            persistence_mode="store_original_only",
            keep_original=True,
            history_entries=["[2026-03-14] Stored bike receipt"],
        )


@pytest.mark.asyncio
async def test_retract_capture_removes_canonical_and_archive_outputs(tmp_path: Path) -> None:
    config = KnowledgeConfig(
        canonical_root=str(tmp_path / "Mehr"),
        archive_root=str(tmp_path / "Nanobot Archive"),
    )
    artifact = tmp_path / "receipt.pdf"
    artifact.write_text("stub", encoding="utf-8")

    service = KnowledgeIntakeService(tmp_path / "workspace", router=KeepOriginalRouter(), config=config)
    queued = await service.capture_file(artifact, user_hint="bike")
    worker = KnowledgeWorker(tmp_path / "workspace", router=KeepOriginalRouter(), config=config)
    await worker.process_once()

    result = service.retract_capture(queued.capture_id)
    job = KnowledgeStore(tmp_path / "workspace", config).load_job(queued.capture_id)

    assert result.status == "retracted"
    assert job.status == "retracted"
    assert not list((tmp_path / "Mehr").glob("**/history.md"))
    assert not list((tmp_path / "Nanobot Archive").glob("**/receipt.pdf"))
    assert (tmp_path / "workspace/retracted" / f"{queued.capture_id}.json").exists()
