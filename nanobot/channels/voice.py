"""Twilio voice-call channel implementation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import threading
from datetime import datetime, timezone
from html import escape as xml_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable
from urllib.parse import parse_qs, urlsplit

import httpx
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel

if TYPE_CHECKING:
    from nanobot.config.schema import VoiceCallConfig


DirectChatFn = Callable[..., Awaitable[str]]


class _VoiceHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server with a back-reference to the channel."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],  # noqa: N803
        channel: "VoiceCallChannel",
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.channel = channel


class _VoiceHandler(BaseHTTPRequestHandler):
    """HTTP handler for Twilio voice webhook requests."""

    server: _VoiceHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        channel = self.server.channel
        path = urlsplit(self.path).path
        if path != channel.config.health_path:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        body = json.dumps({"status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        channel = self.server.channel
        path = urlsplit(self.path).path
        if path != channel.config.webhook_path:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        form: dict[str, list[str]] = parse_qs(raw_body, keep_blank_values=True)

        signature = self.headers.get("X-Twilio-Signature", "")
        signature_url = channel.get_signature_url(self.path)
        if channel.config.validate_signature:
            if not signature:
                self.send_response(403)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Missing signature")
                return
            if not channel.verify_signature(signature_url, form, signature):
                self.send_response(403)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Invalid signature")
                return

        fut = None
        try:
            if channel.loop is None:
                raise RuntimeError("Voice event loop is not ready")
            fut = asyncio.run_coroutine_threadsafe(
                channel.handle_twilio_webhook(form),
                channel.loop,
            )
            timeout = max(5, int(channel.config.request_timeout_seconds))
            twiml = fut.result(timeout=timeout)
        except Exception as e:
            if fut is not None:
                fut.cancel()
            logger.error("Voice webhook processing failed: {}", repr(e))
            twiml = channel.build_say_hangup_twiml(channel.config.fallback_message)

        response_body = twiml.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Silence default noisy HTTP logs.
        try:
            msg = format % args
        except Exception:
            msg = format
        if "/api/ws" in msg:
            return
        logger.debug("voice-http: {}", msg)


class VoiceCallChannel(BaseChannel):
    """Twilio voice-call channel."""

    name = "voice-call"
    display_name = "Voice Call"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        from nanobot.config.schema import VoiceCallConfig

        return VoiceCallConfig().model_dump(by_alias=True)

    def __init__(
        self,
        config: "VoiceCallConfig | dict[str, Any]",
        bus: MessageBus,
        direct_chat: DirectChatFn | None = None,
    ):
        if isinstance(config, dict):
            from nanobot.config.schema import VoiceCallConfig

            config = VoiceCallConfig.model_validate(config)
        super().__init__(config, bus)
        self.config = config
        self._direct_chat = direct_chat
        self._server: _VoiceHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._events_path = Path.home() / ".nanobot" / "voice-calls" / "calls.jsonl"
        self._events_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        return self._loop

    async def start(self) -> None:
        """Start webhook server and wait until stopped."""
        self._running = True
        self._loop = asyncio.get_running_loop()

        try:
            self._server = _VoiceHTTPServer(
                (self.config.bind, int(self.config.port)),
                _VoiceHandler,
                self,
            )
        except OSError as e:
            self._running = False
            logger.error(
                "Voice channel failed to bind {}:{}: {}",
                self.config.bind,
                self.config.port,
                e,
            )
            return

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="nanobot-voice-webhook",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Voice webhook listening on http://{}:{}{}",
            self.config.bind,
            self.config.port,
            self.config.webhook_path,
        )
        logger.info(
            "Voice health endpoint on http://{}:{}{}",
            self.config.bind,
            self.config.port,
            self.config.health_path,
        )

        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop webhook server."""
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    async def send(self, msg: OutboundMessage) -> None:
        """Place an outbound voice call through Twilio."""
        if not self._validate_twilio_credentials():
            logger.warning("Voice outbound call skipped: Twilio credentials missing")
            return

        to_number = msg.chat_id.strip()
        if not to_number:
            logger.warning("Voice outbound call skipped: empty destination number")
            return

        text = (msg.content or "").strip() or "Hello from nanobot."
        twiml = self.build_say_hangup_twiml(text)

        payload = {
            "To": to_number,
            "From": self.config.from_number,
            "Twiml": twiml,
        }
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.account_sid}/Calls.json"

        try:
            async with httpx.AsyncClient(
                timeout=max(10, int(self.config.request_timeout_seconds)),
            ) as client:
                response = await client.post(
                    url,
                    data=payload,
                    auth=(self.config.account_sid, self.config.auth_token),
                )
        except Exception as e:
            logger.error("Voice outbound call failed: {}", e)
            self._log_event("outbound_failed", to=to_number, error=str(e))
            return

        if response.status_code not in (200, 201):
            logger.error(
                "Voice outbound call rejected (status={}): {}",
                response.status_code,
                response.text[:500],
            )
            self._log_event(
                "outbound_failed",
                to=to_number,
                status=response.status_code,
                body=response.text[:500],
            )
            return

        sid = ""
        try:
            sid = response.json().get("sid", "")
        except Exception:
            sid = ""

        self._log_event("outbound_started", to=to_number, call_sid=sid)
        logger.info("Voice outbound call started to {} (sid={})", to_number, sid or "unknown")

    def get_signature_url(self, request_path: str) -> str:
        """Return URL used by Twilio signature verification."""
        path = request_path
        if self.config.public_base_url:
            return self.config.public_base_url.rstrip("/") + path
        return f"http://{self.config.bind}:{self.config.port}{path}"

    def verify_signature(
        self,
        url: str,
        form: dict[str, list[str]],
        signature: str,
    ) -> bool:
        """Verify Twilio request signature."""
        token = self.config.auth_token or ""
        if not token:
            return False

        payload = url
        for key in sorted(form.keys()):
            values = form.get(key, [])
            for value in values:
                payload += key + value
        mac = hmac.new(token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
        expected = base64.b64encode(mac).decode("utf-8")
        return hmac.compare_digest(expected, signature)

    async def handle_twilio_webhook(self, form: dict[str, list[str]]) -> str:
        """Process Twilio webhook and return TwiML."""
        params: dict[str, str] = {}
        for k, values in form.items():
            params[k] = values[-1] if values else ""

        call_sid = params.get("CallSid", "")
        from_number = params.get("From", "")
        call_status = (params.get("CallStatus", "") or "").lower()
        speech = (params.get("SpeechResult") or params.get("Digits") or "").strip()

        self._log_event(
            "webhook",
            call_sid=call_sid,
            from_number=from_number,
            status=call_status,
            speech=speech[:500],
        )

        if call_status in {"completed", "busy", "failed", "no-answer", "canceled"} and not speech:
            return self.build_empty_twiml()

        if not self.is_allowed(from_number):
            self._log_event("blocked", call_sid=call_sid, from_number=from_number)
            return self.build_say_hangup_twiml("This number is not authorized. Goodbye.")

        if not speech:
            return self.build_gather_twiml(self.config.welcome_message)

        if speech.lower() in {"bye", "goodbye", "hang up", "hangup", "stop"}:
            return self.build_say_hangup_twiml("Goodbye.")

        reply = await self._ask_agent(
            from_number=from_number or "unknown",
            call_sid=call_sid or "unknown",
            user_text=speech,
        )
        return self.build_gather_twiml(reply)

    async def _ask_agent(self, from_number: str, call_sid: str, user_text: str) -> str:
        if not self._direct_chat:
            logger.error("Voice direct_chat callback is not configured")
            return self.config.fallback_message

        prompt = (
            "You are speaking to a caller over a phone call. "
            "Respond briefly and naturally with plain text suitable for text-to-speech.\n\n"
            f"Caller ({from_number}) said: {user_text}"
        )
        try:
            timeout = max(5, int(self.config.request_timeout_seconds) - 5)
            reply = await asyncio.wait_for(
                self._direct_chat(
                    content=prompt,
                    session_key=f"voice-call:{call_sid}",
                    channel=self.name,
                    chat_id=from_number,
                ),
                timeout=timeout,
            )
            text = (reply or "").strip()
            if not text:
                text = self.config.fallback_message
            self._log_event(
                "assistant_reply",
                call_sid=call_sid,
                from_number=from_number,
                content=text[:500],
            )
            return text
        except Exception as e:
            logger.error("Voice direct-chat failed: {}", e)
            self._log_event("assistant_error", call_sid=call_sid, from_number=from_number, error=str(e))
            return self.config.fallback_message

    def build_empty_twiml(self) -> str:
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

    def build_say_hangup_twiml(self, text: str) -> str:
        safe_text = xml_escape(text.strip() or self.config.fallback_message)
        voice = xml_escape(self.config.voice)
        language = xml_escape(self.config.language)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say voice="{voice}" language="{language}">{safe_text}</Say>'
            "<Hangup/>"
            "</Response>"
        )

    def build_gather_twiml(self, text: str) -> str:
        safe_text = xml_escape(text.strip() or self.config.fallback_message)
        voice = xml_escape(self.config.voice)
        language = xml_escape(self.config.language)
        timeout = max(1, int(self.config.gather_timeout_seconds))
        action = xml_escape(self.config.webhook_path)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Gather input="speech dtmf" action="{action}" method="POST" '
            f'timeout="{timeout}" speechTimeout="auto">'
            f'<Say voice="{voice}" language="{language}">{safe_text}</Say>'
            "</Gather>"
            f'<Say voice="{voice}" language="{language}">Goodbye.</Say>'
            "<Hangup/>"
            "</Response>"
        )

    def _validate_twilio_credentials(self) -> bool:
        required = [
            bool(self.config.account_sid.strip()),
            bool(self.config.auth_token.strip()),
            bool(self.config.from_number.strip()),
        ]
        return all(required)

    def _log_event(self, event: str, **kwargs: Any) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **kwargs,
        }
        try:
            with open(self._events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            logger.debug("Failed to append voice event to {}", self._events_path)
