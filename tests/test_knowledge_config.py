from pathlib import Path

from nanobot.config.schema import Config
from nanobot.knowledge.models import CaptureJob


def test_knowledge_config_defaults() -> None:
    config = Config.model_validate({})

    assert config.knowledge.enabled is True
    assert config.knowledge.inbox_dir == "inbox"
    assert config.knowledge.entities_dir == "entities"
    assert config.knowledge.ledgers_dir == "ledgers"
    assert config.knowledge.indexes_dir == "indexes"
    assert config.knowledge.review_dir == "inbox/review"
    assert config.knowledge.local_web.enabled is True
    assert config.knowledge.local_web.bind == "127.0.0.1"
    assert config.knowledge.local_web.port == 18791
    assert config.knowledge.native_capture.enabled is False
    assert config.knowledge.native_capture.bind == "127.0.0.1"
    assert config.knowledge.native_capture.port == 18792
    assert config.knowledge.native_capture.auth_token == ""


def test_knowledge_config_defaults_include_queue_and_canonical_targets() -> None:
    config = Config.model_validate({})

    assert config.knowledge.queue_dir == "queue"
    assert config.knowledge.processing_dir == "processing"
    assert config.knowledge.failed_dir == "failed"
    assert config.knowledge.retracted_dir == "retracted"
    assert config.knowledge.logs_dir == "logs"
    assert config.knowledge.canonical_root == "~/Library/Mobile Documents/com~apple~CloudDocs/Mehr"
    assert config.knowledge.archive_root == "~/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive"
    assert config.knowledge.project_memory_enabled is True
    assert config.knowledge.project_memory_dir == "Projects"


def test_capture_job_accepts_project_memory_paths() -> None:
    job = CaptureJob(
        capture_id="cap-123",
        inbox_item_path=Path("/tmp/workspace/queue/cap-123"),
        project_memory_paths=[Path("/tmp/Mehr/Projects/nanobot/decisions.md")],
    )

    assert job.project_memory_paths == [Path("/tmp/Mehr/Projects/nanobot/decisions.md")]
