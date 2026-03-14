# OpenClaw -> nanobot Migration Report (Mac)

Date: 2026-02-22
Host: /Users/mehranmozaffari (macOS)

## 1) Executive Summary

Migration is now in hard-cutover mode to nanobot.

Completed:
- Twilio voice adapter built into nanobot and running in launchd.
- OpenClaw/Clawbot runtime components removed from this Mac.
- Tailscale Funnel routes replaced with nanobot-only endpoints.
- OpenClaw-era GCP Pub/Sub topic (`clawdbot-gmail-watch`) removed.

Current runtime status:
- nanobot LaunchAgent active (`ai.nanobot.gateway`), running on port `18790`.
- Voice webhook active on `3334`.
- Twilio signature validation enabled and verified with signed request.
- Telegram channel enabled.

## 2) What Was Built in nanobot

### 2.1 Twilio voice channel implementation
Code added/updated:
- `nanobot/channels/voice.py`
- `nanobot/config/schema.py`
- `nanobot/channels/manager.py`
- `nanobot/cli/commands.py`
- `tests/test_voice_channel.py`

Capabilities:
- Inbound Twilio webhook (`/voice/webhook`) with TwiML responses.
- Outbound Twilio call support from nanobot outbound bus.
- Caller allowlist support.
- Signature verification support (`X-Twilio-Signature`).
- Health endpoint (`/health`).
- Call event logging (`~/.nanobot/voice-calls/calls.jsonl`).

### 2.2 OpenClaw migration utility
Script:
- `scripts/migrate_openclaw_to_nanobot.py`

Migrates:
- model/workspace defaults
- OpenRouter API key
- Telegram token + allowlist
- Voice/Twilio settings
- OpenClaw cron jobs -> nanobot cron store

## 3) Current nanobot Integrations (Active Inventory)

## 3.1 Channels
From `~/.nanobot/config.json`:
- Telegram: enabled
  - allowFrom: `6250094179`
- Voice Call (Twilio): enabled
  - bind/port: `0.0.0.0:3334`
  - webhook: `/voice/webhook`
  - public base URL: `https://mehrans-mac-mini.taile53526.ts.net`
  - allowFrom: `+61421695316`
  - signature validation: `true`
- WhatsApp: disabled
- Email channel (IMAP/SMTP): disabled
- Discord/Feishu/Mochat/DingTalk/Slack/QQ: disabled

## 3.2 Gateway + Service
- LaunchAgent: `~/Library/LaunchAgents/ai.nanobot.gateway.plist`
- Process: `nanobot gateway --port 18790`
- Logs:
  - `~/.nanobot/logs/gateway.log`
  - `~/.nanobot/logs/gateway.err.log`

## 3.3 Tailscale ingress
Funnel routes now:
- `/voice/webhook` -> `http://127.0.0.1:3334/voice/webhook`

Removed legacy routes:
- `/`
- `/whatsapp/webhook`
- `/voice/stream`
- `/test-ws`
- old root mappings (`18789` and temporary `18790`)

## 3.4 Scheduling / automation
From `~/.nanobot/cron/jobs.json`:
- `daily-briefing` enabled (cron `30 7 * * *`, timezone `Australia/Sydney`)
- Delivery target: Telegram (`6250094179`)
- Uses `gog` commands for Gmail + Calendar aggregation

## 3.5 Filesystem integration
nanobot workspace:
- `/Users/mehranmozaffari/.nanobot/workspace`

Symlinked paths available to nanobot:
- `notes`
- `vault`
- `personal`
- `work`
- `business`
- `contacts`
- `pickleball`

## 3.6 Google account tooling integration used by cron
`gog auth list` shows one active account with scopes including:
- gmail, calendar, drive, contacts, docs, sheets, tasks, etc.

This means the daily briefing flow remains operational under nanobot (not OpenClaw).

## 4) OpenClaw / Clawbot Removal Actions

Removed from host:
- LaunchAgents:
  - `ai.openclaw.gateway.plist` (removed)
  - `com.whatsapp-bridge.plist` (removed)
- User runtime dirs:
  - `~/.openclaw` (removed)
  - `~/.clawdbot` (removed)
  - `~/clawd` (removed)
- App support/prefs:
  - `~/Library/Application Support/OpenClaw` (removed)
  - `~/Library/Application Support/clawdbot` (removed)
  - `~/Library/Application Support/clawdhub` (removed)
  - `~/Library/Preferences/ai.openclaw.shared.plist` (removed)
- Global npm packages:
  - `openclaw` (removed)
  - `clawdbot` (removed)
  - `@clawdbot/voice-call` (removed)
  - `clawdhub` (removed)
- Shell references in active dotfiles (zsh/bash): none found
- Executables in PATH:
  - `openclaw`: not found
  - `clawdbot`: not found
  - `clawdhub`: not found

## 5) Cloud/Gateway Legacy Integration Analysis

Project: `uncover-478919`

Observed and handled:
- Legacy topic `projects/uncover-478919/topics/clawdbot-gmail-watch` existed.
- Topic IAM had Gmail push publisher principal:
  - `serviceAccount:gmail-api-push@system.gserviceaccount.com`
- Topic was deleted during migration cleanup.

Current matching topic left:
- `projects/uncover-478919/topics/gog-gmail-watch`

No Pub/Sub subscriptions currently listed.

Interpretation:
- OpenClaw-specific Gmail push plumbing was left behind and is now removed.
- Remaining `gog-gmail-watch` topic appears tied to current `gog` tooling rather than OpenClaw.

## 6) Validation Results

- `nanobot channels status` shows Telegram + Voice enabled.
- launchd job `ai.nanobot.gateway` is running.
- `lsof` confirms voice webhook listener on `3334`.
- `curl` local webhook tests return TwiML responses.
- Signed Twilio-style request accepted (HTTP 200).
- Unsigned request rejected after hardening (HTTP 403 Missing signature).
- External funnel webhook test to `https://.../voice/webhook` returns TwiML successfully.
- Test suite: `67 passed`.

## 7) Remaining Residuals (Non-Operational)

Historical references to OpenClaw/Clawbot still exist in archival/log locations (not active runtime):
- `~/.config/superpowers/conversation-archive/...`
- `~/.config/gcloud/logs/...`

These are records, not running integrations.

## 8) Migration Completion State

Hard migration status: COMPLETE for runtime cutover.

- Production runtime path is nanobot-only.
- OpenClaw/Clawbot services and packages are removed.
- Twilio voice adapter is active in nanobot and verified.
- Filesystem + cron + Telegram integrations are available under nanobot.

## 9) Recommended Post-Cutover Follow-up

1. Rotate API secrets used during migration (OpenRouter/Twilio/Telegram) if they were exposed in any prior logs or chats.
2. Optionally purge historical archives/logs containing OpenClaw references if you want zero historical traces.
3. If you want to retire the old Telegram bot identity (`@mehran_clawdbot`), create a new bot token and update `~/.nanobot/config.json`.
