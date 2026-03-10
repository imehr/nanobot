"""Local web inbox for text-based knowledge capture."""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def build_capture_response(
    *,
    inbox_item_path: Path,
    entities: list[str],
    actions: list[str],
    follow_up: str | None,
) -> str:
    """Build the JSON response payload for a capture request."""
    return json.dumps(
        {
            "inbox_item_path": str(inbox_item_path),
            "entities": entities,
            "actions": actions,
            "follow_up": follow_up,
        }
    )


class LocalWebInboxServer:
    """A small JSON-only local inbox server."""

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

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/capture":
                    self._send(404, json.dumps({"error": "not_found"}))
                    return
                if auth_token:
                    provided = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                    if provided != auth_token:
                        self._send(401, json.dumps({"error": "unauthorized"}))
                        return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    content_text = str(payload.get("content_text", "")).strip()
                    user_hint = str(payload.get("user_hint", "")).strip()
                    if not content_text:
                        self._send(400, json.dumps({"error": "content_text_required"}))
                        return
                    result = asyncio.run(
                        intake_service.capture_text(
                            content_text,
                            user_hint=user_hint,
                            source="web-inbox",
                        )
                    )
                    self._send(
                        200,
                        build_capture_response(
                            inbox_item_path=result.inbox_item_path,
                            entities=result.entities,
                            actions=result.actions,
                            follow_up=result.follow_up.question if result.follow_up else None,
                        ),
                    )
                except Exception as exc:  # pragma: no cover - defensive server path
                    self._send(500, json.dumps({"error": str(exc)}))

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
