from pathlib import Path

from nanobot.knowledge.store import KnowledgeStore


def test_knowledge_store_bootstraps_workspace(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)

    store.bootstrap()

    assert (tmp_path / "inbox").is_dir()
    assert (tmp_path / "entities").is_dir()
    assert (tmp_path / "ledgers").is_dir()
    assert (tmp_path / "indexes").is_dir()
    assert (tmp_path / "inbox" / "review").is_dir()
