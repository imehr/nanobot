"""AI routing for captured knowledge items."""

from __future__ import annotations

from typing import Any

from nanobot.knowledge.models import InboxItem, IntakeDecision


_SAVE_INTAKE_DECISION_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_intake_decision",
            "description": "Return the structured routing decision for a captured knowledge item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entities": {"type": "array", "items": {"type": "string"}},
                    "material_type": {"type": "string"},
                    "persistence_mode": {"type": "string"},
                    "project_name": {"type": "string"},
                    "project_memory_actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "target": {"type": "string"},
                                "summary": {"type": "string"},
                                "title": {"type": "string"},
                                "slug": {"type": "string"},
                            },
                            "required": ["target", "summary"],
                        },
                    },
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "section": {"type": "string"},
                                "key": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["key", "value"],
                        },
                    },
                    "history_entries": {"type": "array", "items": {"type": "string"}},
                    "ledger_rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ledger": {"type": "string"},
                                "row": {"type": "object"},
                            },
                            "required": ["ledger", "row"],
                        },
                    },
                    "keep_original": {"type": "boolean"},
                    "follow_up": {
                        "anyOf": [
                            {
                                "type": "object",
                                "properties": {"question": {"type": "string"}},
                                "required": ["question"],
                            },
                            {"type": "null"},
                        ]
                    },
                },
                "required": ["entities", "material_type", "persistence_mode"],
            },
        },
    }
]


class KnowledgeRouter:
    """Convert captured material into a normalized intake decision."""

    def __init__(self, provider: Any, model: str) -> None:
        self.provider = provider
        self.model = model

    async def route(self, item: InboxItem, current_memory: str) -> IntakeDecision:
        prompt = (
            "Classify and route this captured knowledge item. "
            "Return only a save_intake_decision tool call.\n\n"
            f"Current memory:\n{current_memory or '(empty)'}\n\n"
            f"User hint: {item.user_hint or '(none)'}\n"
            f"Content:\n{item.content_text or '(empty)'}"
        )
        response = await self.provider.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a routing agent. Decide where captured material should be stored.",
                },
                {"role": "user", "content": prompt},
            ],
            tools=_SAVE_INTAKE_DECISION_TOOL,
            model=self.model,
            max_tokens=1200,
            temperature=0.0,
        )

        if not getattr(response, "has_tool_calls", False):
            finish = getattr(response, "finish_reason", "unknown")
            content = getattr(response, "content", "") or ""
            import logging
            logging.getLogger(__name__).warning(
                "KnowledgeRouter: no tool call from model (finish_reason=%s). "
                "Content preview: %.200s",
                finish,
                content,
            )
            raise RuntimeError(
                f"KnowledgeRouter: model did not call save_intake_decision "
                f"(finish_reason={finish})"
            )

        args = response.tool_calls[0].arguments
        return IntakeDecision.model_validate(args)
