import base64
import hashlib
import hmac

import pytest

from nanobot.bus.queue import MessageBus
from nanobot.channels.voice import VoiceCallChannel
from nanobot.config.schema import VoiceCallConfig


def _make_channel(
    *,
    allow_from: list[str] | None = None,
    reply: str = "Hello from nanobot",
) -> VoiceCallChannel:
    cfg = VoiceCallConfig(
        enabled=True,
        account_sid="AC123",
        auth_token="token123",
        from_number="+15550000000",
        allow_from=allow_from or [],
    )

    async def _direct_chat(**kwargs):
        return reply

    channel = VoiceCallChannel(cfg, MessageBus(), direct_chat=_direct_chat)
    return channel


def test_verify_signature_matches_twilio_algorithm() -> None:
    channel = _make_channel()
    url = "https://example.com/voice/webhook"
    form = {
        "CallSid": ["CA123"],
        "From": ["+15551112222"],
    }
    payload = url + "CallSidCA123From+15551112222"
    digest = hmac.new(b"token123", payload.encode("utf-8"), hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode("utf-8")

    assert channel.verify_signature(url, form, signature) is True
    assert channel.verify_signature(url, form, "invalid") is False


def test_build_gather_twiml_contains_gather_action() -> None:
    channel = _make_channel()
    twiml = channel.build_gather_twiml("How can I help?")

    assert "<Gather" in twiml
    assert 'action="/voice/webhook"' in twiml
    assert "How can I help?" in twiml


@pytest.mark.asyncio
async def test_webhook_rejects_unauthorized_caller(tmp_path) -> None:
    channel = _make_channel(allow_from=["+15559998888"])
    channel._events_path = tmp_path / "calls.jsonl"
    channel._events_path.parent.mkdir(parents=True, exist_ok=True)

    twiml = await channel.handle_twilio_webhook(
        {
            "From": ["+15551112222"],
            "CallSid": ["CA123"],
        }
    )
    assert "not authorized" in twiml.lower()
    assert "<Hangup/>" in twiml


@pytest.mark.asyncio
async def test_webhook_processes_speech_with_agent(tmp_path) -> None:
    channel = _make_channel(allow_from=["+15551112222"], reply="Sure, I can do that.")
    channel._events_path = tmp_path / "calls.jsonl"
    channel._events_path.parent.mkdir(parents=True, exist_ok=True)

    twiml = await channel.handle_twilio_webhook(
        {
            "From": ["+15551112222"],
            "CallSid": ["CA456"],
            "SpeechResult": ["Can you check my tasks?"],
        }
    )
    assert "Sure, I can do that." in twiml
    assert "<Gather" in twiml
