import pytest

from nanobot.knowledge.models import InboxItem
from nanobot.knowledge.router import KnowledgeRouter


class ProjectMemoryProvider:
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
                            "entities": ["Work/projects/nanobot"],
                            "material_type": "reference",
                            "persistence_mode": "store_all",
                            "project_name": "nanobot",
                            "project_memory_actions": [
                                {
                                    "target": "decisions",
                                    "summary": "2026-03-14: Capture processing moved to queued background work.",
                                },
                                {
                                    "target": "timeline",
                                    "summary": "2026-03-14: Added Mehr project memory summaries.",
                                },
                                {
                                    "target": "feature",
                                    "title": "Queued Mehr Memory",
                                    "slug": "queued-mehr-memory",
                                    "summary": "Captures now queue locally and write canonical summaries into Mehr.",
                                },
                            ],
                            "follow_up": None,
                        },
                    },
                )()
            ]

        return Response()


class TemporaryNoteProvider:
    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.0):
        class Response:
            has_tool_calls = True
            content = None
            tool_calls = [
                type(
                    "Call",
                    (),
                    {
                        "id": "call-2",
                        "name": "save_intake_decision",
                        "arguments": {
                            "entities": ["Work/projects/nanobot"],
                            "material_type": "temporary",
                            "persistence_mode": "ignore",
                            "project_name": "nanobot",
                            "project_memory_actions": [],
                            "follow_up": None,
                        },
                    },
                )()
            ]

        return Response()


@pytest.mark.asyncio
async def test_router_parses_project_memory_actions_for_significant_changes() -> None:
    router = KnowledgeRouter(provider=ProjectMemoryProvider(), model="test-model")
    item = InboxItem(content_text="We moved capture processing into a queued background worker.", user_hint="nanobot")

    decision = await router.route(item, current_memory="Nanobot project memory")

    assert decision.project_name == "nanobot"
    assert [action.target for action in decision.project_memory_actions] == ["decisions", "timeline", "feature"]
    assert decision.project_memory_actions[2].slug == "queued-mehr-memory"


@pytest.mark.asyncio
async def test_router_keeps_project_memory_empty_for_temporary_notes() -> None:
    router = KnowledgeRouter(provider=TemporaryNoteProvider(), model="test-model")
    item = InboxItem(content_text="Temporary debug scratchpad", user_hint="nanobot")

    decision = await router.route(item, current_memory="Nanobot project memory")

    assert decision.project_name == "nanobot"
    assert decision.project_memory_actions == []
