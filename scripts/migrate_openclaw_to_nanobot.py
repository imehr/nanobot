#!/usr/bin/env python3
"""Migrate local OpenClaw user config into nanobot config/cron."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_openclaw_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    # OpenClaw config can contain trailing commas.
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)


def _ensure(obj: dict, key: str) -> dict:
    if key not in obj or not isinstance(obj[key], dict):
        obj[key] = {}
    return obj[key]


def _extract_openrouter_key(openclaw_home: Path) -> str:
    auth = _load_json(openclaw_home / "agents" / "main" / "agent" / "auth.json")
    if isinstance(auth.get("openrouter"), dict):
        key = auth["openrouter"].get("key", "")
        if isinstance(key, str):
            return key
    return ""


def _extract_telegram_allow_from(openclaw_home: Path) -> list[str]:
    allow = _load_json(openclaw_home / "credentials" / "telegram-allowFrom.json")
    values = allow.get("allowFrom", [])
    return [str(v) for v in values] if isinstance(values, list) else []


def _migrate_config(openclaw_home: Path, nanobot_home: Path) -> None:
    openclaw = _load_openclaw_json(openclaw_home / "openclaw.json")
    config_path = nanobot_home / "config.json"
    config = _load_json(config_path)

    agents = _ensure(config, "agents")
    defaults = _ensure(agents, "defaults")
    channels = _ensure(config, "channels")
    providers = _ensure(config, "providers")

    # Workspace/model
    agent_list = (((openclaw.get("agents") or {}).get("list")) or [])
    main_agent = next((a for a in agent_list if isinstance(a, dict) and a.get("id") == "main"), None)
    if isinstance(main_agent, dict):
        workspace = main_agent.get("workspace")
        model = main_agent.get("model")
        if isinstance(workspace, str) and workspace:
            defaults["workspace"] = workspace
        if isinstance(model, str) and model:
            defaults["model"] = model

    # OpenRouter key
    openrouter_key = _extract_openrouter_key(openclaw_home)
    if openrouter_key:
        _ensure(providers, "openrouter")["apiKey"] = openrouter_key

    # Telegram
    oc_tg = ((openclaw.get("channels") or {}).get("telegram")) or {}
    tg = _ensure(channels, "telegram")
    token = oc_tg.get("botToken", "")
    if isinstance(token, str) and token:
        tg["enabled"] = True
        tg["token"] = token
    allow_from = _extract_telegram_allow_from(openclaw_home)
    if allow_from:
        tg["allowFrom"] = allow_from

    # Voice call (Twilio)
    vc = ((((openclaw.get("plugins") or {}).get("entries") or {}).get("voice-call") or {}).get("config") or {})
    twilio = vc.get("twilio") if isinstance(vc.get("twilio"), dict) else {}
    serve = vc.get("serve") if isinstance(vc.get("serve"), dict) else {}

    voice = _ensure(channels, "voiceCall")
    if twilio.get("accountSid") and twilio.get("authToken") and vc.get("fromNumber"):
        voice["enabled"] = True
        voice["accountSid"] = twilio["accountSid"]
        voice["authToken"] = twilio["authToken"]
        voice["fromNumber"] = vc["fromNumber"]
        voice["allowFrom"] = vc.get("allowFrom", []) if isinstance(vc.get("allowFrom"), list) else []
        voice["bind"] = serve.get("bind", "0.0.0.0")
        voice["port"] = serve.get("port", 3334)
        voice["webhookPath"] = serve.get("path", "/voice/webhook")
        voice["validateSignature"] = not bool(vc.get("skipSignatureVerification", False))

        public_url = vc.get("publicUrl", "")
        if isinstance(public_url, str) and public_url:
            parts = urlsplit(public_url)
            voice["publicBaseUrl"] = f"{parts.scheme}://{parts.netloc}"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _migrate_cron(openclaw_home: Path, nanobot_home: Path) -> None:
    openclaw_jobs = _load_json(openclaw_home / "cron" / "jobs.json")
    jobs = openclaw_jobs.get("jobs", []) if isinstance(openclaw_jobs, dict) else []

    # Reset nanobot cron store.
    cron_path = nanobot_home / "cron" / "jobs.json"
    if cron_path.exists():
        cron_path.unlink()

    if not jobs:
        return

    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    service = CronService(cron_path)
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if not job.get("enabled", True):
            continue
        schedule = job.get("schedule", {})
        payload = job.get("payload", {})
        delivery = job.get("delivery", {})

        kind = schedule.get("kind")
        if kind == "every":
            sched = CronSchedule(kind="every", every_ms=schedule.get("everyMs"))
        elif kind == "at":
            sched = CronSchedule(kind="at", at_ms=schedule.get("atMs"))
        elif kind == "cron":
            sched = CronSchedule(
                kind="cron",
                expr=schedule.get("expr"),
                tz=schedule.get("tz"),
            )
        else:
            continue

        deliver = bool(delivery)
        channel = delivery.get("channel") if isinstance(delivery, dict) else None
        to = delivery.get("to") if isinstance(delivery, dict) else None
        message = payload.get("message", "")

        if not isinstance(message, str) or not message.strip():
            continue

        service.add_job(
            name=str(job.get("name", "migrated-job")),
            schedule=sched,
            message=message,
            deliver=deliver,
            channel=channel,
            to=to,
        )


def _ensure_workspace_memory(nanobot_home: Path) -> None:
    cfg = _load_json(nanobot_home / "config.json")
    workspace = (((cfg.get("agents") or {}).get("defaults") or {}).get("workspace")) or ""
    if not isinstance(workspace, str) or not workspace:
        return
    workspace_path = Path(workspace).expanduser()
    memory_dir = workspace_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_file = memory_dir / "MEMORY.md"
    history_file = memory_dir / "HISTORY.md"
    if not memory_file.exists():
        memory_file.write_text(
            "# Long-term Memory\n\n"
            "Migrated from OpenClaw environment. Use this as the canonical persistent memory store.\n",
            encoding="utf-8",
        )
    if not history_file.exists():
        history_file.write_text("", encoding="utf-8")


def main() -> None:
    home = Path.home()
    openclaw_home = home / ".openclaw"
    nanobot_home = home / ".nanobot"
    if not openclaw_home.exists():
        raise SystemExit(f"OpenClaw home not found: {openclaw_home}")

    _migrate_config(openclaw_home, nanobot_home)
    _migrate_cron(openclaw_home, nanobot_home)
    _ensure_workspace_memory(nanobot_home)
    print("Migration complete: config, cron, and workspace memory initialized.")


if __name__ == "__main__":
    main()
