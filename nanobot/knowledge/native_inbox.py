"""Loopback-only native capture server for the macOS app and Share extension."""

from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from python_multipart import parse_form

from nanobot.knowledge.web_inbox import build_capture_response


def build_job_status_payload(job) -> dict[str, object]:
    primary_path = ""
    if job.project_memory_paths:
        primary_path = str(job.project_memory_paths[0])
    elif job.canonical_paths:
        primary_path = str(job.canonical_paths[0])
    elif job.archive_paths:
        primary_path = str(job.archive_paths[0])
    else:
        primary_path = str(job.inbox_item_path)
    return {
        "capture_id": job.capture_id,
        "status": job.status,
        "source_channel": job.source_channel,
        "capture_type": job.capture_type,
        "inbox_item_path": str(job.inbox_item_path),
        "primary_path": primary_path,
        "canonical_paths": [str(path) for path in job.canonical_paths],
        "archive_paths": [str(path) for path in job.archive_paths],
        "project_memory_paths": [str(path) for path in job.project_memory_paths],
        "follow_up": job.follow_up or None,
        "error": job.error or None,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
    }


class NativeCaptureServer:
    """A small local-only inbox server for native macOS clients."""

    def __init__(
        self,
        *,
        bind: str,
        port: int,
        intake_service: Any,
        auth_token: str = "",
    ) -> None:
        self.bind = bind
        self.port = port
        self.intake_service = intake_service
        self.auth_token = auth_token
        self._server = ThreadingHTTPServer((bind, port), self._make_handler())
        self._thread: threading.Thread | None = None

    def _make_handler(self):
        intake_service = self.intake_service
        auth_token = self.auth_token

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status: int, body: str, content_type: str = "application/json") -> None:
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self._send(200, json.dumps({"status": "ok"}))
                    return
                if auth_token:
                    provided = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                    if provided != auth_token:
                        self._send(401, json.dumps({"error": "unauthorized"}))
                        return
                if self.path == "/captures/recent":
                    jobs = intake_service.store.list_recent_jobs()
                    self._send(200, json.dumps({"captures": [build_job_status_payload(job) for job in jobs]}))
                    return
                if self.path.startswith("/captures/"):
                    capture_id = self.path.removeprefix("/captures/").strip("/")
                    try:
                        job = intake_service.store.load_job(capture_id)
                    except FileNotFoundError:
                        self._send(404, json.dumps({"error": "not_found"}))
                        return
                    self._send(200, json.dumps(build_job_status_payload(job)))
                    return
                self._send(404, json.dumps({"error": "not_found"}))

            def do_POST(self) -> None:  # noqa: N802
                provided = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                if auth_token and provided != auth_token:
                    self._send(401, json.dumps({"error": "unauthorized"}))
                    return
                if self.path == "/capture":
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        content_type = self.headers.get("Content-Type", "")
                        body = self.rfile.read(length)
                        if "multipart/form-data" in content_type:
                            result = self._handle_multipart_capture(body, content_type)
                        else:
                            result = self._handle_json_capture(body)
                        self._send(
                            202,
                            build_capture_response(
                                capture_id=result.capture_id,
                                status=result.status,
                                inbox_item_path=result.inbox_item_path,
                                entities=result.entities,
                                actions=result.actions,
                                project_memory_paths=result.project_memory_paths,
                                follow_up=result.follow_up.question if result.follow_up else None,
                            ),
                        )
                    except Exception as exc:  # pragma: no cover - defensive server path
                        self._send(500, json.dumps({"error": str(exc)}))
                    return
                if self.path.endswith("/retract") and self.path.startswith("/captures/"):
                    capture_id = self.path.removeprefix("/captures/").removesuffix("/retract")
                    try:
                        result = intake_service.retract_capture(capture_id)
                        job = intake_service.store.load_job(capture_id)
                    except FileNotFoundError:
                        self._send(404, json.dumps({"error": "not_found"}))
                        return
                    self._send(200, json.dumps(build_job_status_payload(job)))
                    return
                if self.path.endswith("/retry") and self.path.startswith("/captures/"):
                    capture_id = self.path.removeprefix("/captures/").removesuffix("/retry")
                    try:
                        intake_service.store.retry_job(capture_id)
                        job = intake_service.store.load_job(capture_id)
                    except FileNotFoundError:
                        self._send(404, json.dumps({"error": "not_found"}))
                        return
                    self._send(200, json.dumps(build_job_status_payload(job)))
                    return
                self._send(404, json.dumps({"error": "not_found"}))

            def _handle_json_capture(self, body: bytes):
                payload = json.loads(body or b"{}")
                content_text = str(payload.get("content_text", "")).strip()
                user_hint = str(payload.get("user_hint", "")).strip()
                if not content_text:
                    raise ValueError("content_text_required")
                return asyncio.run(
                    intake_service.capture_text(
                        content_text,
                        user_hint=user_hint,
                        source="native-app",
                    )
                )

            def _handle_multipart_capture(self, body: bytes, content_type: str):
                fields: dict[str, str] = {}
                uploaded: list[str] = []

                def on_field(field) -> None:
                    name = field.field_name.decode() if isinstance(field.field_name, bytes) else str(field.field_name)
                    value = field.value.decode() if isinstance(field.value, bytes) else str(field.value)
                    fields[name] = value

                def on_file(file) -> None:
                    filename = file.file_name.decode() if isinstance(file.file_name, bytes) else str(file.file_name)
                    suffix = Path(filename).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                        file.file_object.seek(0)
                        handle.write(file.file_object.read())
                        uploaded.append(handle.name)

                parse_form(
                    {
                        "Content-Type": content_type.encode(),
                        "Content-Length": str(len(body)).encode(),
                    },
                    io.BytesIO(body),
                    on_field,
                    on_file,
                )
                content_text = fields.get("content_text", "").strip()
                user_hint = fields.get("user_hint", "").strip()
                if not uploaded:
                    raise ValueError("file_required")
                path = Path(uploaded[0])
                try:
                    return asyncio.run(
                        intake_service.capture_file(
                            path,
                            user_hint=user_hint,
                            source="native-app",
                            content_text=content_text,
                        )
                    )
                finally:
                    if path.exists():
                        os.unlink(path)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        return Handler

    def start(self) -> None:
        """Start the inbox server on a background thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the inbox server and wait briefly for shutdown."""
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
