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
