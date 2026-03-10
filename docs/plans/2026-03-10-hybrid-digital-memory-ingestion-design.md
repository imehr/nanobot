# Hybrid Digital Memory Ingestion Design

**Date:** 2026-03-10

**Goal**

Add a hybrid digital memory system to `nanobot` that can ingest raw material from local devices and remote chat channels, preserve originals, extract durable facts, route transactional data into ledgers, and answer later questions from canonical memory instead of ad hoc chat history.

**Current State**

- `nanobot` already supports multiple inbound chat channels including Telegram and WhatsApp through `nanobot gateway`.
- Incoming media can already be downloaded by some channels and passed into the agent context.
- Persistent memory today is a two-layer system:
  - `workspace/memory/MEMORY.md` for long-term facts loaded into context
  - `workspace/memory/HISTORY.md` for append-only searchable history
- The current memory model is conversation-oriented, not artifact-oriented:
  - there is no canonical entity store for things like a bike or a house,
  - there is no first-class inbox for raw material,
  - there is no transaction ledger for receipts or recurring costs,
  - there is no routing layer that decides how a screenshot, invoice, or pasted note should be stored and later retrieved.

**Problem**

The desired behavior is not just “remember this fact.” The system needs to accept raw material such as screenshots, receipts, forwarded messages, clipboard text, PDFs, photos, and voice notes, then decide:

- what the material is about,
- which real-world entity or entities it belongs to,
- whether the original file must be preserved,
- which durable facts should become canonical memory,
- whether a dated event should be appended to history,
- whether a ledger row should be created,
- and when a follow-up question is necessary because classification affects downstream use.

This needs to work across:

- Mac-native local capture flows,
- other machines on the local network,
- and mobile devices both at home and away from home.

## Requirements

### Functional

- Accept incoming raw material from multiple frontends:
  - local watched folder,
  - local web inbox,
  - existing chat channels such as Telegram and WhatsApp,
  - future native Mac share-sheet / clipboard / screenshot helpers.
- Preserve the original artifact before any AI classification or transformation.
- Support at least these material types:
  - plain text,
  - screenshots and images,
  - PDFs and other uploaded files,
  - links,
  - voice notes and transcripts when available.
- Classify each item into one or more entities such as:
  - `personal/bike`,
  - `personal/house`,
  - `personal/me`,
  - `business/<entity>`,
  - `finance/expense`.
- Decide the persistence mode for each item:
  - original only,
  - extracted facts only,
  - original plus facts,
  - original plus history,
  - original plus ledger row,
  - quarantine for review.
- Support cross-domain routing.
  - Example: a bike service invoice belongs to the bike, to expenses, and possibly to tax or reimbursement tracking.
- Ask follow-up questions only when ambiguity changes storage, retrieval, or financial treatment.

### Retrieval

- Stable reusable facts must be answered from canonical entity memory first.
- Time-based answers must come from entity history or ledgers before raw artifacts.
- Original artifacts must remain retrievable for proof and detailed inspection.
- Stored facts, events, and ledger rows should link back to the source artifact where possible.

### Operational

- The design must preserve compatibility with the current `MEMORY.md` / `HISTORY.md` model.
- New storage should live under the existing workspace, not in a separate hidden silo.
- The system should be safe against low-confidence classification:
  - store first,
  - quarantine when needed,
  - ask one short follow-up question instead of making a bad irreversible choice.
- The taxonomy must be able to evolve over time as new entities and categories emerge.

## Proposed Architecture

### 1. One ingestion backend, many capture frontends

Do not force one app on every device. Instead, build one ingestion backend and allow different frontends to send material into it.

Recommended frontends:

- **Mac primary**
  - local watched folder,
  - local web inbox,
  - later: Share Sheet target, clipboard shortcut, screenshot action, menu bar helper.
- **Other local machines**
  - local web inbox over the LAN,
  - later: lightweight desktop helper.
- **Mobile**
  - Telegram and/or WhatsApp for universal remote reach,
  - later: direct mobile web share flow if a secure public endpoint is exposed.

All frontends should submit the same logical envelope:

- raw content or file path,
- original filename if present,
- source device/app/channel,
- capture type,
- optional user hint such as “bike” or “expense”,
- timestamp,
- checksum or fingerprint for deduplication.

### 2. Hybrid storage model under the workspace

Use the workspace as the source of truth, with richer structure than the current two-file memory model.

Recommended top-level layout:

- `inbox/`
  - raw arrivals before routing
- `inbox/review/`
  - low-confidence items awaiting clarification
- `entities/`
  - canonical knowledge organized by real-world entities
- `ledgers/`
  - structured records such as expenses and maintenance logs
- `indexes/`
  - cross-links, extracted fields, and dedup metadata
- `memory/`
  - compact agent-facing summaries compatible with the existing prompt system

Entity structure example:

- `entities/personal/bike/profile.md`
- `entities/personal/bike/history.md`
- `entities/personal/bike/artifacts/`
- `entities/personal/bike/service/`
- `entities/personal/bike/insurance/`

Ledger examples:

- `ledgers/expenses.csv`
- `ledgers/maintenance_log.csv`
- `ledgers/subscriptions.csv`
- `ledgers/insurance_policies.csv`

### 3. Keep `MEMORY.md` as compact working memory, not the full archive

`memory/MEMORY.md` should remain the small always-loaded context file for the agent, but it should no longer be the only canonical store.

Recommended role:

- summarize durable facts and active priorities,
- point to canonical entity files,
- stay compact enough for prompt usage,
- avoid storing full receipts, long OCR dumps, or dense ledgers.

`memory/HISTORY.md` remains useful for coarse conversation/event recall, but source-of-truth domain data should live under `entities/`, `ledgers/`, and `artifacts/`.

### 4. AI decision engine for routing

Each submitted item should go through a routing decision that outputs:

- matched entities,
- material type,
- persistence mode,
- canonical destinations,
- extracted facts,
- event entries,
- ledger rows,
- follow-up question if needed.

Material-type examples:

- `durable_fact`
- `event`
- `transaction`
- `document`
- `reference`
- `temporary_noise`

Persistence-mode examples:

- `store_original_only`
- `store_original_and_extract_facts`
- `store_original_and_append_history`
- `store_original_and_add_ledger_row`
- `store_all`
- `quarantine`

Examples:

- Tire pressure note:
  - update `entities/personal/bike/profile.md`
  - optionally append a source note reference
- Service receipt:
  - save original under bike artifacts
  - append service event to bike history
  - add row to `ledgers/expenses.csv`
  - optionally add row to `ledgers/maintenance_log.csv`
- Insurance policy screenshot:
  - save original
  - update policy facts in bike profile or insurance ledger
  - ask follow-up only if ownership or business use is ambiguous

### 5. Retrieval should prefer canonical layers over raw search

Retrieval order should be:

1. entity `profile.md`
2. entity `history.md`
3. ledgers
4. artifacts
5. raw inbox as fallback

This ensures:

- “What is my front tire pressure?” comes from bike profile
- “How much did I pay for the last service?” comes from the expense/maintenance records
- “Show me the invoice” returns the original artifact

### 6. Explicit capture mode first, ambient behavior later

For the first implementation, use an explicit ingestion path instead of trying to reinterpret every ordinary conversation turn as structured memory intake.

That means:

- local inbox submissions are treated as capture items,
- watched-folder files are treated as capture items,
- chat submissions can opt into capture mode through metadata or a lightweight capture command/convention,
- ordinary conversational chat stays on the current agent path.

This keeps the first release understandable and reduces accidental over-capture.

### 7. Progressive learning from corrections

The system should record:

- routing corrections,
- category overrides,
- entity merges/splits,
- and personal/business/tax classification decisions.

Those corrections can later improve prompts and heuristics without hard-coding every rule upfront.

## Decision Rules

### Always do first

- Save the original artifact into the inbox with stable metadata.

### Prefer silent routing when confidence is high

- If an item clearly belongs to a known entity and the downstream handling is obvious, do not ask unnecessary questions.

### Ask questions only when they matter

Good reasons to ask:

- personal vs business,
- one-off vs recurring,
- whether a new fact replaces or supplements an existing fact,
- whether an expense is tax-relevant or reimbursable,
- whether a document applies to more than one entity.

Bad reasons to ask:

- confirming obvious entity matches,
- asking for metadata already visible in the file,
- delaying storage of the original.

### Quarantine instead of guessing badly

When confidence is low:

- preserve the artifact,
- save extracted text and candidate routes,
- move it to `inbox/review/`,
- ask one concise follow-up.

## Phased Rollout

### Phase 1: ingestion backbone

- workspace storage layout
- inbox metadata and artifact preservation
- explicit AI routing decisions
- entity/profile/history writers
- expenses and maintenance ledgers
- compatibility summary updates for `memory/MEMORY.md`

### Phase 2: practical capture

- local web inbox for LAN devices
- watched-folder ingestion for Mac
- reuse Telegram and WhatsApp as remote/mobile capture channels

### Phase 3: richer analysis and retrieval

- OCR for screenshots and receipts
- stronger deduplication
- source linking across facts, events, and ledgers
- retrieval helpers and search indexes

### Phase 4: native UX and adaptation

- Mac Share Sheet target
- clipboard and screenshot shortcuts
- menu bar helper
- learning from user corrections and new entity patterns

## Decisions

- The correct storage model is hybrid, not file-only and not spreadsheet-only.
- The system should use one ingestion backend with many frontends.
- Telegram/WhatsApp are acceptable for mobile and remote reach, but not the primary Mac workflow.
- Canonical knowledge should live in structured workspace files and ledgers, while `MEMORY.md` stays compact and prompt-friendly.
- Originals must be preserved before AI interpretation.
- Retrieval must favor canonical entity/ledger data over raw chat recall.

## Out Of Scope

- Building the full native Mac Share Sheet or menu bar application in the first implementation.
- Automatically reclassifying every normal conversation message as memory intake from day one.
- Full OCR/transcription coverage for every document format in the first milestone.
- Public internet exposure of the local web inbox without a separate security design.
