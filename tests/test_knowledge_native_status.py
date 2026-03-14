from __future__ import annotations

from pathlib import Path

import httpx

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import InboxItem
from nanobot.knowledge.service import CaptureResult, KnowledgeIntakeService
from nanobot.knowledge.store import KnowledgeStore


class FakeRouter:
    async def route(self, item, current_memory):
        raise AssertionError("router should not be called in status test")


class FakeIntakeService(KnowledgeIntakeService):
    def __init__(self, workspace: Path, config: KnowledgeConfig) -> None:
        super().__init__(workspace, router=FakeRouter(), config=config)

    async def capture_text(self, content_text: str, *, user_hint: str = "", source: str = "local") -> CaptureResult:
        return await super().capture_text(content_text, user_hint=user_hint, source=source)


def test_native_inbox_exposes_recent_and_single_capture_status(tmp_path: Path) -> None:
    from nanobot.knowledge.native_inbox import NativeCaptureServer

    config = KnowledgeConfig(
        canonical_root=str(tmp_path / "Mehr"),
        archive_root=str(tmp_path / "Nanobot Archive"),
    )
    workspace = tmp_path / "workspace"
    service = FakeIntakeService(workspace, config)
    store = KnowledgeStore(workspace, config)
    queued = store.enqueue_capture(InboxItem(content_text="Bike note", source="telegram"))
    completed = store.transition_job(
        queued.capture_id,
        status="completed",
        canonical_paths=[tmp_path / "Mehr/Personal/motorbike/bmw-c400gt.md"],
    )
    failed = store.enqueue_capture(InboxItem(content_text="Bike error", source="whatsapp"))
    store.transition_job(failed.capture_id, status="failed", error="bad parse")

    server = NativeCaptureServer(bind="127.0.0.1", port=0, intake_service=service, auth_token="status-secret")
    server.start()
    try:
        port = server._server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"

        recent = httpx.get(
            f"{base_url}/captures/recent",
            headers={"Authorization": "Bearer status-secret"},
            timeout=5,
        )
        assert recent.status_code == 200
        payload = recent.json()["captures"]
        assert len(payload) == 2
        assert payload[0]["capture_id"] in {completed.capture_id, failed.capture_id}
        assert {item["source_channel"] for item in payload} == {"telegram", "whatsapp"}

        single = httpx.get(
            f"{base_url}/captures/{completed.capture_id}",
            headers={"Authorization": "Bearer status-secret"},
            timeout=5,
        )
        assert single.status_code == 200
        assert single.json()["status"] == "completed"
        assert single.json()["primary_path"].endswith("bmw-c400gt.md")
    finally:
        server.stop()
