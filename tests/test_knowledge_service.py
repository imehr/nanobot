import pytest

from nanobot.knowledge.models import FollowUpRequest, IntakeDecision
from nanobot.knowledge.service import KnowledgeIntakeService


class FakeRouter:
    async def route(self, item, current_memory):
        return IntakeDecision(
            entities=["personal/bike"],
            material_type="transaction",
            persistence_mode="store_all",
            follow_up=FollowUpRequest(question="Is this personal or business?"),
        )


@pytest.mark.asyncio
async def test_capture_service_enqueues_text_capture_without_routing_inline(tmp_path) -> None:
    service = KnowledgeIntakeService.for_testing(tmp_path, router=FakeRouter())

    result = await service.capture_text("Bike service receipt", user_hint="bike")

    assert result.status == "queued"
    assert result.capture_id
    assert result.inbox_item_path.exists()
    assert (tmp_path / "queue" / f"{result.capture_id}.json").exists()
    assert not list((tmp_path / "entities").glob("**/*"))


@pytest.mark.asyncio
async def test_capture_service_stages_uploaded_file_and_returns_queue_job(tmp_path) -> None:
    class FileRouter:
        async def route(self, item, current_memory):
            return IntakeDecision(
                entities=["personal/bike"],
                material_type="document",
                persistence_mode="store_original_only",
                keep_original=True,
            )

    artifact = tmp_path / "invoice.pdf"
    artifact.write_text("pdf-stub", encoding="utf-8")
    service = KnowledgeIntakeService.for_testing(tmp_path, router=FileRouter())

    result = await service.capture_file(artifact, user_hint="bike")

    assert result.status == "queued"
    assert result.capture_id
    assert result.inbox_item_path.exists()
    assert (result.inbox_item_path / "attachments" / "invoice.pdf").exists()
    assert (tmp_path / "queue" / f"{result.capture_id}.json").exists()
