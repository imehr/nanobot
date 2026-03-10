from pathlib import Path

from nanobot.knowledge.watcher import discover_new_files


def test_discover_new_files_skips_seen_entries(tmp_path: Path) -> None:
    watched = tmp_path / "watched"
    watched.mkdir()
    item = watched / "receipt.txt"
    item.write_text("bike receipt", encoding="utf-8")

    first = discover_new_files([watched], seen=set())
    second = discover_new_files([watched], seen={str(item.resolve())})

    assert str(item.resolve()) in first
    assert second == []
