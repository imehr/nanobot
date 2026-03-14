from __future__ import annotations

import json
from pathlib import Path

import httpx

from nanobot.knowledge.models import CaptureJob
from nanobot.knowledge.service import CaptureResult


class FakeIntakeService:
    def __init__(self) -> None:
        self.text_calls: list[dict[str, str]] = []
        self.file_calls: list[dict[str, str | bool]] = []

    async def capture_text(self, content_text: str, *, user_hint: str = "", source: str = "local") -> CaptureResult:
        self.text_calls.append(
            {
                "content_text": content_text,
                "user_hint": user_hint,
                "source": source,
            }
        )
        return CaptureResult(
            capture_id="cap-text-1",
            status="queued",
            inbox_item_path=Path("/tmp/native-text"),
            entities=["personal/bike"],
            actions=["saved original", "queued"],
        )

    async def capture_file(
        self,
        file_path: Path,
        *,
        user_hint: str = "",
        source: str = "local",
        content_text: str = "",
    ) -> CaptureResult:
        self.file_calls.append(
            {
                "file_path": str(file_path),
                "file_exists": file_path.exists(),
                "user_hint": user_hint,
                "source": source,
                "content_text": content_text,
            }
        )
        return CaptureResult(
            capture_id="cap-file-1",
            status="queued",
            inbox_item_path=Path("/tmp/native-file"),
            entities=["personal/bike"],
            actions=["saved original", "queued"],
        )


def test_native_inbox_health_and_capture(tmp_path: Path) -> None:
    from nanobot.knowledge.native_inbox import NativeCaptureServer

    intake = FakeIntakeService()
    server = NativeCaptureServer(
        bind="127.0.0.1",
        port=0,
        intake_service=intake,
        auth_token="secret-token",
    )
    server.start()
    try:
        port = server._server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"

        health = httpx.get(f"{base_url}/health", timeout=5)
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        unauthorized = httpx.post(
            f"{base_url}/capture",
            json={"content_text": "Front tire pressure is 35 psi", "user_hint": "bike"},
            timeout=5,
        )
        assert unauthorized.status_code == 401
        assert unauthorized.json() == {"error": "unauthorized"}

        authorized = httpx.post(
            f"{base_url}/capture",
            headers={"Authorization": "Bearer secret-token"},
            json={"content_text": "Front tire pressure is 35 psi", "user_hint": "bike"},
            timeout=5,
        )
        assert authorized.status_code == 202
        assert authorized.json()["status"] == "queued"
        assert authorized.json()["capture_id"] == "cap-text-1"
        assert authorized.json()["entities"] == ["personal/bike"]
        assert intake.text_calls == [
            {
                "content_text": "Front tire pressure is 35 psi",
                "user_hint": "bike",
                "source": "native-app",
            }
        ]

        upload = httpx.post(
            f"{base_url}/capture",
            headers={"Authorization": "Bearer secret-token"},
            data={"content_text": "Service invoice", "user_hint": "bike"},
            files={"file": ("invoice.txt", b"paid 199.00", "text/plain")},
            timeout=5,
        )
        assert upload.status_code == 202
        assert upload.json()["status"] == "queued"
        assert upload.json()["capture_id"] == "cap-file-1"
        assert upload.json()["entities"] == ["personal/bike"]
        assert intake.file_calls == [
            {
                "file_path": intake.file_calls[0]["file_path"],
                "file_exists": True,
                "user_hint": "bike",
                "source": "native-app",
                "content_text": "Service invoice",
            }
        ]
    finally:
        server.stop()


def test_build_job_status_payload_prefers_project_memory_path() -> None:
    from nanobot.knowledge.native_inbox import build_job_status_payload

    job = CaptureJob(
        capture_id="cap-123",
        status="completed",
        source_channel="mac_app",
        capture_type="file",
        inbox_item_path=Path("/tmp/workspace/inbox/cap-123"),
        canonical_paths=[Path("/tmp/Mehr/Work/projects/nanobot/index.md")],
        archive_paths=[Path("/tmp/Nanobot Archive/2026/nanobot/cap-123/receipt.png")],
        project_memory_paths=[Path("/tmp/Mehr/Projects/nanobot/decisions.md")],
    )

    payload = build_job_status_payload(job)

    assert payload["primary_path"] == "/tmp/Mehr/Projects/nanobot/decisions.md"
    assert payload["project_memory_paths"] == ["/tmp/Mehr/Projects/nanobot/decisions.md"]
