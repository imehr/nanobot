"""Local web inbox for text-based knowledge capture."""

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


def build_inbox_page() -> str:
    """Build a simple browser UI for local capture."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>nanobot inbox</title>
  <style>
    :root {
      --paper: #f4efe2;
      --ink: #1d1a14;
      --muted: #746b5f;
      --panel: #fffaf0;
      --accent: #c46a2f;
      --accent-dark: #9f4d1c;
      --line: rgba(29, 26, 20, 0.16);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(196,106,47,0.16), transparent 30%),
        linear-gradient(135deg, #efe4c8, var(--paper));
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      display: grid;
      place-items: center;
      padding: 24px;
    }
    .shell {
      width: min(760px, 100%);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 24px 80px rgba(29, 26, 20, 0.12);
      overflow: hidden;
    }
    .hero {
      padding: 32px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.65), rgba(255,255,255,0));
    }
    h1 {
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.2rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
      text-transform: lowercase;
    }
    .sub {
      margin: 0;
      color: var(--muted);
      max-width: 44rem;
      font-size: 1rem;
      line-height: 1.5;
    }
    form {
      padding: 28px 32px 32px;
      display: grid;
      gap: 18px;
    }
    label {
      display: grid;
      gap: 8px;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }
    textarea, input[type="text"], input[type="file"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.72);
      padding: 14px 16px;
      font: inherit;
      color: var(--ink);
    }
    textarea {
      min-height: 168px;
      resize: vertical;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 16px;
    }
    .actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 14px 22px;
      background: linear-gradient(135deg, var(--accent), var(--accent-dark));
      color: white;
      font: inherit;
      font-weight: 600;
      letter-spacing: 0.02em;
      cursor: pointer;
      box-shadow: 0 12px 24px rgba(159, 77, 28, 0.28);
    }
    .hint {
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.5;
      max-width: 30rem;
    }
    @media (max-width: 680px) {
      .grid { grid-template-columns: 1fr; }
      .hero, form { padding-left: 20px; padding-right: 20px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>nanobot inbox</h1>
      <p class="sub">Drop in the raw thing. A note, a screenshot, a receipt, a PDF. Nanobot stores the original first, then decides what belongs in memory, history, and ledgers.</p>
    </section>
    <form action="/capture" method="post" enctype="multipart/form-data">
      <label>
        Context
        <textarea name="content_text" placeholder="Example: this is my regular bike service centre and this invoice is for the 10,000 km service"></textarea>
      </label>
      <div class="grid">
        <label>
          Hint
          <input type="text" name="user_hint" placeholder="bike, house, expense, subscription">
        </label>
        <label>
          Attachment
          <input type="file" name="file" multiple>
        </label>
      </div>
      <div class="actions">
        <p class="hint">Use the note for context. Use the hint only when you want to bias routing. Files are preserved before any AI interpretation.</p>
        <button type="submit">Capture to memory</button>
      </div>
    </form>
  </main>
</body>
</html>"""


def build_result_page(
    *,
    entities: list[str],
    actions: list[str],
    follow_up: str | None,
) -> str:
    """Build a human-facing result page for browser submissions."""
    entity_html = "".join(f"<li>{entity}</li>" for entity in entities) or "<li>unclassified</li>"
    action_html = "".join(f"<li>{action}</li>" for action in actions) or "<li>saved</li>"
    follow_up_html = (
        f'<section class="panel accent"><h2>Follow-up</h2><p>{follow_up}</p></section>'
        if follow_up
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>capture saved</title>
  <style>
    :root {{
      --paper: #f4efe2;
      --ink: #1d1a14;
      --muted: #746b5f;
      --panel: #fffaf0;
      --line: rgba(29, 26, 20, 0.16);
      --accent: #c46a2f;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      background: linear-gradient(135deg, #efe4c8, var(--paper));
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    .shell {{
      width: min(700px, 100%);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 24px 80px rgba(29, 26, 20, 0.12);
    }}
    h1 {{ margin: 0 0 16px; font-size: clamp(2rem, 4vw, 3rem); line-height: 0.95; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      background: rgba(255,255,255,0.6);
    }}
    .accent {{ border-color: rgba(196,106,47,0.4); background: rgba(196,106,47,0.08); }}
    h2 {{ margin: 0 0 10px; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
    ul {{ margin: 0; padding-left: 18px; }}
    a {{
      display: inline-block;
      margin-top: 18px;
      color: white;
      background: var(--accent);
      padding: 12px 18px;
      border-radius: 999px;
      text-decoration: none;
    }}
    @media (max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <h1>captured</h1>
    <div class="grid">
      <section class="panel">
        <h2>Entities</h2>
        <ul>{entity_html}</ul>
      </section>
      <section class="panel">
        <h2>Actions</h2>
        <ul>{action_html}</ul>
      </section>
    </div>
    {follow_up_html}
    <a href="/">Capture another item</a>
  </main>
</body>
</html>"""

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
    """A small local inbox server for browser and JSON capture."""

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
                if self.path != "/":
                    self._send(404, "not found", "text/plain; charset=utf-8")
                    return
                self._send(200, build_inbox_page(), "text/html; charset=utf-8")

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
                    content_type = self.headers.get("Content-Type", "")
                    body = self.rfile.read(length)
                    if "multipart/form-data" in content_type:
                        results = self._handle_multipart_capture(body, content_type)
                        entities = sorted({entity for result in results for entity in result.entities})
                        actions = [action for result in results for action in result.actions]
                        follow_up = next(
                            (result.follow_up.question for result in results if result.follow_up is not None),
                            None,
                        )
                        self._send(
                            200,
                            build_result_page(
                                entities=entities,
                                actions=actions,
                                follow_up=follow_up,
                            ),
                            "text/html; charset=utf-8",
                        )
                        return
                    else:
                        result = self._handle_json_capture(body)
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
                        source="web-inbox",
                    )
                )

            def _handle_multipart_capture(self, body: bytes, content_type: str):
                fields: dict[str, str] = {}
                uploaded: list[tuple[str, str]] = []

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
                        uploaded.append((handle.name, filename))

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
                if uploaded:
                    results = []
                    try:
                        for temp_path, _filename in uploaded:
                            path = Path(temp_path)
                            results.append(
                                asyncio.run(
                                    intake_service.capture_file(
                                        path,
                                        user_hint=user_hint,
                                        source="web-inbox",
                                        content_text=content_text,
                                    )
                                )
                            )
                        return results
                    finally:
                        for temp_path, _filename in uploaded:
                            path = Path(temp_path)
                            if path.exists():
                                os.unlink(path)
                if not content_text:
                    raise ValueError("content_text_required")
                return [asyncio.run(
                    intake_service.capture_text(
                        content_text,
                        user_hint=user_hint,
                        source="web-inbox",
                    )
                )]

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
