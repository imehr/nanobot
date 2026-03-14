from pathlib import Path

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.store import KnowledgeStore


def test_project_memory_helpers_seed_and_append_files(tmp_path: Path) -> None:
    config = KnowledgeConfig(
        canonical_root=str(tmp_path / "Mehr"),
        archive_root=str(tmp_path / "Nanobot Archive"),
        project_memory_dir="Projects",
    )
    store = KnowledgeStore(tmp_path / "workspace", config)

    seeded = store.ensure_project_memory_project(
        "nanobot",
        repo_path=Path("/Users/mehranmozaffari/Documents/github/nanobot"),
        summary="AI agent and memory system",
    )
    decision_path = store.append_project_memory_decision(
        "nanobot",
        "2026-03-14: Moved capture processing to queued background work.",
    )
    timeline_path = store.append_project_memory_timeline(
        "nanobot",
        "2026-03-14: Added project memory summaries in Mehr.",
    )
    feature_path = store.write_project_memory_feature(
        "nanobot",
        slug="queued-mehr-memory",
        title="Queued Mehr Memory",
        summary="Captures now queue locally and write canonical summaries into Mehr.",
    )

    project_dir = tmp_path / "Mehr/Projects/nanobot"
    assert seeded["project_dir"] == project_dir
    assert seeded["index"] == project_dir / "index.md"
    assert seeded["decisions"] == project_dir / "decisions.md"
    assert seeded["timeline"] == project_dir / "timeline.md"
    assert seeded["links"] == project_dir / "links.md"
    assert seeded["index"].read_text(encoding="utf-8").startswith("# nanobot")
    assert "/Users/mehranmozaffari/Documents/github/nanobot" in seeded["links"].read_text(encoding="utf-8")
    assert "Moved capture processing" in decision_path.read_text(encoding="utf-8")
    assert "Added project memory summaries" in timeline_path.read_text(encoding="utf-8")
    assert feature_path == project_dir / "features/queued-mehr-memory.md"
    assert "Queued Mehr Memory" in feature_path.read_text(encoding="utf-8")
