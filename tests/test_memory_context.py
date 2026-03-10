from pathlib import Path

from nanobot.agent.memory import MemoryStore
from nanobot.knowledge.store import KnowledgeStore


def test_memory_context_includes_compact_knowledge_summary(tmp_path: Path) -> None:
    ks = KnowledgeStore(tmp_path)
    ks.bootstrap()
    profile = tmp_path / "entities/personal/bike/profile.md"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("# Bike\n\n- Front tire pressure: 35 psi\n", encoding="utf-8")

    memory = MemoryStore(tmp_path)

    context = memory.get_memory_context()

    assert "Front tire pressure" in context
