from pathlib import Path

from nanobot.knowledge.models import InboxItem
from nanobot.knowledge.store import KnowledgeStore


def test_enqueue_capture_creates_queued_job_and_runtime_state(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)

    item = InboxItem(content_text="Front tire pressure is 35 psi", user_hint="bike", source="mac_app")
    job = store.enqueue_capture(item)

    assert job.capture_id
    assert job.status == "queued"
    assert job.source_channel == "mac_app"
    assert job.capture_type == "text"
    assert job.inbox_item_path == tmp_path / "inbox" / item.item_id
    assert (tmp_path / "queue" / f"{job.capture_id}.json").exists()


def test_load_job_returns_latest_queue_state(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)

    item = InboxItem(content_text="This is my bike insurer", source="telegram")
    job = store.enqueue_capture(item)

    loaded = store.load_job(job.capture_id)

    assert loaded.capture_id == job.capture_id
    assert loaded.status == "queued"
    assert loaded.source_channel == "telegram"
