import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.knowledge.service import CaptureResult


class DummyProvider:
    def get_default_model(self):
        return "test-model"


class FakeKnowledgeService:
    async def capture_text(self, content_text: str, *, user_hint: str = "", source: str = "local"):
        return CaptureResult(
            inbox_item_path=None,
            entities=["personal/bike"],
            actions=["saved original", "updated bike history"],
        )

    async def capture_file(self, file_path, *, user_hint: str = "", source: str = "local"):
        return CaptureResult(
            inbox_item_path=None,
            entities=["personal/bike"],
            actions=[f"saved {file_path.name}"],
        )


@pytest.mark.asyncio
async def test_capture_mode_routes_to_knowledge_service(tmp_path) -> None:
    loop = AgentLoop(
        bus=MessageBus(),
        provider=DummyProvider(),
        workspace=tmp_path,
        knowledge_service=FakeKnowledgeService(),
    )
    msg = InboundMessage(
        channel="telegram",
        sender_id="1",
        chat_id="1",
        content="Bike receipt",
        metadata={"capture_mode": True, "user_hint": "bike"},
    )

    response = await loop._process_message(msg)

    assert response is not None
    assert "personal/bike" in response.content


@pytest.mark.asyncio
async def test_capture_mode_routes_media_to_knowledge_service(tmp_path) -> None:
    artifact = tmp_path / "invoice.pdf"
    artifact.write_text("pdf-stub", encoding="utf-8")
    loop = AgentLoop(
        bus=MessageBus(),
        provider=DummyProvider(),
        workspace=tmp_path,
        knowledge_service=FakeKnowledgeService(),
    )
    msg = InboundMessage(
        channel="telegram",
        sender_id="1",
        chat_id="1",
        content="Bike receipt",
        media=[str(artifact)],
        metadata={"capture_mode": True, "user_hint": "bike"},
    )

    response = await loop._process_message(msg)

    assert response is not None
    assert "saved invoice.pdf" in response.content
