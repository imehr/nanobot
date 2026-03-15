import json
from pathlib import Path

import httpx

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import InboxItem
from nanobot.knowledge.service import CaptureResult, KnowledgeIntakeService
from nanobot.knowledge.store import KnowledgeStore
from nanobot.knowledge.web_inbox import build_capture_response, build_inbox_page, build_result_page


class FakeRouter:
    async def route(self, item, current_memory):
        raise AssertionError("router should not be called in status test")


class FakeIntakeService(KnowledgeIntakeService):
    def __init__(self, workspace: Path, config: KnowledgeConfig) -> None:
        super().__init__(workspace, router=FakeRouter(), config=config)

    async def capture_text(self, content_text: str, *, user_hint: str = "", source: str = "local") -> CaptureResult:
        return await super().capture_text(content_text, user_hint=user_hint, source=source)


def test_build_capture_response_includes_follow_up() -> None:
    payload = build_capture_response(
        capture_id="cap-123",
        status="queued",
        inbox_item_path=Path("/tmp/item"),
        entities=["personal/bike"],
        actions=["saved original", "updated bike history"],
        project_memory_paths=[Path("/tmp/Mehr/Projects/nanobot/decisions.md")],
        follow_up="Is this personal or business?",
    )

    body = json.loads(payload)

    assert body["capture_id"] == "cap-123"
    assert body["status"] == "queued"
    assert body["entities"] == ["personal/bike"]
    assert body["project_memory_paths"] == ["/tmp/Mehr/Projects/nanobot/decisions.md"]
    assert body["follow_up"] == "Is this personal or business?"


def test_build_inbox_page_includes_upload_form() -> None:
    page = build_inbox_page()

    assert "Nanobot Capture" in page
    assert "nanobot inbox" not in page
    assert 'method="post"' in page.lower()
    assert 'enctype="multipart/form-data"' in page
    assert 'type="file"' in page.lower()
    assert "multiple" in page.lower()
    assert "capture-shell" in page
    assert "capture-header" in page
    assert "capture-composer" in page
    assert "capture-footer" in page
    assert "recent-captures" in page
    assert "Paste Clipboard" in page
    assert "attachment-dropzone" in page
    assert "captureStatus" in page
    assert "captureRecentList" in page


def test_build_result_page_shows_entities_and_actions() -> None:
    page = build_result_page(
        entities=["personal/bike"],
        actions=["saved original", "applied decision"],
        follow_up=None,
    )

    assert "personal/bike" in page
    assert "saved original" in page


def test_web_inbox_exposes_recent_and_single_capture_status(tmp_path: Path) -> None:
    from nanobot.knowledge.web_inbox import LocalWebInboxServer

    config = KnowledgeConfig(
        canonical_root=str(tmp_path / "Mehr"),
        archive_root=str(tmp_path / "Nanobot Archive"),
    )
    workspace = tmp_path / "workspace"
    service = FakeIntakeService(workspace, config)
    store = KnowledgeStore(workspace, config)
    queued = store.enqueue_capture(InboxItem(content_text="Bike note", source="web-inbox"))
    completed = store.transition_job(
        queued.capture_id,
        status="completed",
        canonical_paths=[tmp_path / "Mehr/Personal/motorbike/bmw-c400gt.md"],
    )

    server = LocalWebInboxServer(bind="127.0.0.1", port=0, intake_service=service, auth_token="status-secret")
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
        assert payload[0]["capture_id"] == completed.capture_id
        assert payload[0]["primary_path"].endswith("bmw-c400gt.md")

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
