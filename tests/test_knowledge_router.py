import pytest

from nanobot.knowledge.models import InboxItem
from nanobot.knowledge.router import KnowledgeRouter


class FakeProvider:
    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.0):
        class Response:
            has_tool_calls = True
            content = None
            tool_calls = [
                type(
                    "Call",
                    (),
                    {
                        "id": "call-1",
                        "name": "save_intake_decision",
                        "arguments": {
                            "entities": ["personal/bike"],
                            "material_type": "transaction",
                            "persistence_mode": "store_all",
                            "facts": [{"section": "Specs", "key": "Front tire pressure", "value": "35 psi"}],
                            "history_entries": ["[2026-03-10] Bike serviced"],
                            "ledger_rows": [{"ledger": "expenses", "row": {"amount": "180.00"}}],
                            "follow_up": None,
                        },
                    },
                )()
            ]
        return Response()


@pytest.mark.asyncio
async def test_router_returns_structured_decision() -> None:
    router = KnowledgeRouter(provider=FakeProvider(), model="test-model")
    item = InboxItem(content_text="Bike service receipt", user_hint="bike")

    decision = await router.route(item, current_memory="Known bike facts")

    assert decision.entities == ["personal/bike"]
    assert decision.material_type == "transaction"
    assert decision.ledger_rows[0].ledger == "expenses"
