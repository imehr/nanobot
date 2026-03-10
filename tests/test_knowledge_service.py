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
async def test_capture_service_saves_item_before_follow_up(tmp_path) -> None:
    service = KnowledgeIntakeService.for_testing(tmp_path, router=FakeRouter())

    result = await service.capture_text("Bike service receipt", user_hint="bike")

    assert result.follow_up.question == "Is this personal or business?"
    assert result.inbox_item_path.exists()


@pytest.mark.asyncio
async def test_capture_service_preserves_uploaded_file(tmp_path) -> None:
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

    assert result.inbox_item_path.exists()
    assert (result.inbox_item_path / "attachments" / "invoice.pdf").exists()
