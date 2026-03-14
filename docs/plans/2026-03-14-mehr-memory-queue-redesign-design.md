# Mehr Memory Queue Redesign

**Date:** 2026-03-14

## Goal

Redesign Nanobot capture so incoming material is staged locally, processed asynchronously, and written canonically into `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr`. The local workspace should become operational state only, `Drop to Nanobot` should be temporary intake only, and preserved originals should be archived outside `Mehr` to avoid duplicate material inside the canonical memory tree.

## Source Of Truth

Canonical memory lives in:

- `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr`

Nanobot runtime/staging lives in:

- `~/.nanobot/workspace`

Preserved original artifacts live in:

- `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive`

Temporary local file-drop intake lives in:

- `~/Drop to Nanobot`

## Why This Redesign

The current implementation saves every capture into `~/.nanobot/workspace/inbox` and routes it synchronously during the request. That creates four problems:

1. `workspace/inbox` behaves like a second permanent memory tree instead of temporary intake.
2. The app reports a raw runtime path instead of the real organized destination the user cares about.
3. Retraction/deletion is incomplete because canonical writes and preserved originals are not tracked as one unit of work.
4. Capture feels brittle because a single UI request is responsible for persistence, AI routing, canonical writes, and user feedback.

The redesigned model treats capture as a queued job with an observable lifecycle. It keeps local runtime state separate from canonical memory, makes `Mehr` the only organized source of truth, and gives the Mac app and mobile channels a consistent tracking story.

## Recommended Architecture

### 1. Queue-Based Processing

Every capture creates a local job record with a stable `capture_id`. The initial submission only stages the material and acknowledges the job. A background worker performs AI analysis, canonical writes, archive preservation, and status updates.

Queue state lives under `~/.nanobot/workspace`, for example:

- `queue/`
- `processing/`
- `failed/`
- `retracted/`
- `logs/`
- `jobs.jsonl` or equivalent indexed state

These are runtime artifacts only. They are not the user-facing memory system.

### 2. Canonical Write Target Is Mehr

After processing, Nanobot writes into the existing iCloud structure rooted at:

- `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr`

This structure already contains useful domains such as:

- `Personal/motorbike`
- `Personal/finance`
- `Personal/house`
- `Business/subscriptions.md`
- `Vault/Vehicles`
- `Vault/Insurance`
- `Vault/Finance`

Nanobot may refine and extend this structure when necessary, but it should build on the existing organization rather than maintaining a parallel `entities/` tree under `~/.nanobot/workspace`.

### 3. Preserved Originals Go Outside Mehr

When the AI decision determines that the original artifact should be kept, Nanobot stores it under:

- `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive`

Suggested layout:

- `Nanobot Archive/<year>/<domain-or-entity>/<capture_id>/...`

This keeps `Mehr` clean for other tools that also read it, while still preserving receipts, invoices, screenshots, policies, PDFs, and similar evidence when needed. Canonical notes in `Mehr` should link to the archived original where relevant instead of embedding duplicate copies.

## Capture Channels

All channels feed the same queue model:

- Mac app
- macOS Share extension
- `~/Drop to Nanobot`
- local web inbox
- Telegram
- WhatsApp

Each queued job records:

- `capture_id`
- `source_channel`
- `source_device`
- `captured_at`
- `original_filename`
- `user_hint`
- `content_type`
- queue status

The same status model applies to every channel:

- `queued`
- `processing`
- `needs_input`
- `completed`
- `failed`
- `retracted`

## Routing And Canonicalization

The AI processor decides:

- what entity/domain the item belongs to
- whether it is a stable fact, a dated event, a transaction, a document, or low-value transient input
- whether the original should be preserved
- what canonical files in `Mehr` should be updated
- whether follow-up input is required

Preservation rule:

- Preserve originals for durable evidence such as receipts, invoices, screenshots with long-term value, PDFs, policies, contracts, and record photos.
- Do not preserve low-value transient captures by default, such as short clipboard notes or trivial reminders, unless explicitly requested or inferred to be necessary.

Canonical writes should favor compact, link-centric memory:

- stable facts update the relevant note or profile in `Mehr`
- dated events append to the correct timeline/history note
- transactions update the relevant ledger or finance note
- durable originals remain outside `Mehr` and are linked from it

## App And Share UX

The current Nanobot Capture window layout should be preserved as the visual baseline, but its behavior changes from synchronous save to queued processing.

### Mac App

The app should:

- submit captures into the local queue
- immediately show `Queued`
- then update to `Processing...`
- then show `Saved to Mehr`, `Needs input`, `Failed`, or `Retracted`
- show the primary canonical destination in `Mehr`
- optionally show the archive path when an original was preserved
- show the source channel for recent jobs, including mobile submissions

The app should include a `Recent Captures` view or panel for operational visibility. That list should show captures from all channels, not just the Mac app.

### Progress Feedback

Submitting a capture should visibly indicate activity. The app should show:

- disabled primary action while the request is staging the job
- spinner or busy indicator
- status text such as `Queuing capture...` or `Processing...`

The current silent save behavior is insufficient.

### Share Extension

The macOS Share extension must continue to work with the same queue. It should:

- submit into the same queued pipeline
- show a clear success state after submission
- not require the main app to be open

### Window Behavior

Opening capture repeatedly should reuse the main window rather than leave duplicate capture windows around. Header and footer must remain persistent while only the center content scrolls.

## Delete / Retract Model

Deletion should become a first-class `Retract capture` operation.

Retracting a capture should:

1. locate the queued job by `capture_id`
2. remove canonical writes from `Mehr`
3. remove preserved originals from `Nanobot Archive`
4. record a small local tombstone under `~/.nanobot/workspace/retracted`
5. mark the job `retracted`

This preserves operational history without leaving the capture in active retrieval.

Deleting only a raw intake folder is not sufficient and should no longer be the user-facing model.

## Operational Logging

Operational logs should not be stored in `Mehr`.

Recommended split:

- `Mehr` = canonical memory
- `Nanobot Archive` = preserved original artifacts
- `~/.nanobot/workspace` = queue state, processing logs, failure records, tombstones
- `NanobotCapture.app` = human-facing control panel for recent jobs and recovery actions

This keeps the memory tree clean while still making capture behavior inspectable.

## Error Handling

If a capture cannot be processed:

- the job stays in local runtime state
- status becomes `failed`
- the app shows the failure message and `Retry`

If classification requires clarification:

- status becomes `needs_input`
- the pending question is stored against the job
- the question is surfaced in the Mac app and, where appropriate, replied back through Telegram or WhatsApp

## Testing Strategy

Implementation should be verified at four layers:

1. queue/job lifecycle tests
2. canonical write and archive preservation tests
3. retract/delete rollback tests
4. app/share/channel integration tests

Key end-to-end scenarios:

- pasted screenshot from the Mac app queues and later lands in the correct `Mehr` destination
- receipt from Telegram is tracked in recent captures and writes canonical + archive outputs
- file dropped into `~/Drop to Nanobot` is processed and the temporary intake is cleared after success
- retract removes the canonical `Mehr` writes and any preserved archive artifact

## Non-Goals For This Pass

- full knowledge-browsing UI inside the Mac app
- exposing operational logs in `Mehr`
- making the queue state itself part of the canonical memory system
- public internet exposure of the local queue endpoint beyond existing mobile/chat paths

## Summary

The target system is:

- `Mehr` in iCloud as the only canonical memory tree
- `Nanobot Archive` in iCloud for preserved originals
- `~/.nanobot/workspace` for local queue and runtime state only
- asynchronous queue-based processing for every channel
- explicit progress and recent-capture tracking in the Mac app
- real retract/delete behavior that removes linked canonical and archive writes
