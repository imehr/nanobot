from pathlib import Path

import pytest

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import InboxItem, IntakeDecision, ProjectMemoryAction
from nanobot.knowledge.store import KnowledgeStore
from nanobot.knowledge.worker import KnowledgeWorker


class ProjectMemoryRouter:
    async def route(self, item, current_memory):
        return IntakeDecision(
            entities=["Work/projects/nanobot"],
            material_type="reference",
            persistence_mode="store_all",
            project_name="nanobot",
            project_memory_actions=[
                ProjectMemoryAction(
                    target="decisions",
                    summary="2026-03-14: Added a project memory layer in Mehr.",
                ),
                ProjectMemoryAction(
                    target="timeline",
                    summary="2026-03-14: Queued captures can now summarize meaningful project work.",
                ),
                ProjectMemoryAction(
                    target="feature",
                    title="Project Memory Layer",
                    slug="project-memory-layer",
                    summary="Important project decisions and milestones are summarized under Mehr/Projects.",
                ),
            ],
        )


@pytest.mark.asyncio
async def test_worker_writes_project_memory_and_tracks_paths(tmp_path: Path) -> None:
    config = KnowledgeConfig(
        canonical_root=str(tmp_path / "Mehr"),
        archive_root=str(tmp_path / "Nanobot Archive"),
        project_memory_dir="Projects",
    )
    store = KnowledgeStore(tmp_path / "workspace", config)
    job = store.enqueue_capture(InboxItem(content_text="We added project memory summaries.", source="mac_app"))
    worker = KnowledgeWorker(tmp_path / "workspace", router=ProjectMemoryRouter(), config=config)

    processed = await worker.process_once()
    loaded = store.load_job(job.capture_id)

    assert processed is not None
    assert loaded.status == "completed"
    assert loaded.project_memory_paths == [
        tmp_path / "Mehr/Projects/nanobot/decisions.md",
        tmp_path / "Mehr/Projects/nanobot/timeline.md",
        tmp_path / "Mehr/Projects/nanobot/features/project-memory-layer.md",
    ]
    assert "project memory layer" in loaded.project_memory_paths[0].read_text(encoding="utf-8").lower()
    assert loaded.project_memory_paths[2].exists()
