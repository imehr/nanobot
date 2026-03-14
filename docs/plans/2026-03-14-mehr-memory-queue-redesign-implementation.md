# Mehr Memory Queue Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace synchronous workspace-centric capture with a queued pipeline that stages locally, writes canonical memory into `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr`, archives preserved originals under `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive`, and exposes progress/retract state in the Mac capture app.

**Architecture:** All capture channels enqueue a local job in `~/.nanobot/workspace` and return an immediate acknowledgement. A background worker processes jobs, writes organized outputs into `Mehr`, stores durable originals in `Nanobot Archive`, and records per-job status/results for the Mac app, Share extension, and mobile/chat channels. The local workspace becomes operational runtime only: queue state, logs, failures, and retract tombstones.

**Tech Stack:** Python, pytest, dataclasses, local filesystem queue/state, SwiftUI, AppKit paste handling, Xcode/xcodebuild

---

### Task 1: Create an isolated implementation worktree

**Files:**
- Create: `.worktrees/codex/mehr-memory-queue-redesign` via `git worktree`

**Step 1: Create the worktree on a `codex/` branch**

Run:

```bash
git worktree add .worktrees/codex-mehr-memory-queue-redesign -b codex/mehr-memory-queue-redesign
```

Expected: new worktree exists with a clean checkout of the new branch.

**Step 2: Verify the worktree is isolated**

Run:

```bash
git -C .worktrees/codex-mehr-memory-queue-redesign status --short
```

Expected: no local changes inside the new worktree.

**Step 3: Commit**

No commit for this task. The worktree is setup only.

### Task 2: Add queue/archive/Mehr configuration

**Files:**
- Modify: `nanobot/config/schema.py`
- Test: `tests/test_knowledge_config.py`

**Step 1: Write the failing config test**

Add assertions for new config fields such as:

```python
def test_knowledge_config_defaults_include_queue_and_mehr_targets():
    config = KnowledgeConfig()
    assert config.queue_dir == "queue"
    assert config.processing_dir == "processing"
    assert config.failed_dir == "failed"
    assert config.retracted_dir == "retracted"
    assert config.logs_dir == "logs"
    assert "Mehr" in str(config.canonical_root)
    assert "Nanobot Archive" in str(config.archive_root)
```

**Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_config.py -k queue -v
```

Expected: FAIL because the new fields do not exist yet.

**Step 3: Add minimal schema support**

Extend `KnowledgeConfig` with explicit queue/runtime/canonical/archive settings, including:

- local queue/runtime directory names
- canonical root path for `Mehr`
- archive root path for `Nanobot Archive`
- local retention/pruning settings

Use defaults matching the approved design.

**Step 4: Run the config test**

Run:

```bash
pytest tests/test_knowledge_config.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_knowledge_config.py nanobot/config/schema.py
git commit -m "feat: add Mehr queue capture config"
```

### Task 3: Introduce queue job models and runtime state storage

**Files:**
- Modify: `nanobot/knowledge/models.py`
- Modify: `nanobot/knowledge/store.py`
- Create: `tests/test_knowledge_queue.py`

**Step 1: Write failing tests for queue state storage**

Add tests covering:

- enqueueing a text capture creates a stable `capture_id`
- queue job files are written under runtime state, not canonical memory
- job status transitions can be read back

Example:

```python
def test_enqueue_text_capture_creates_queued_job(tmp_path: Path):
    store = KnowledgeStore(tmp_path, KnowledgeConfig())
    job = store.enqueue_text_capture("hello", user_hint="bike", source="mac_app")
    assert job.status == "queued"
    assert job.capture_id
    assert (tmp_path / "queue" / f"{job.capture_id}.json").exists()
```

**Step 2: Run the new queue tests**

Run:

```bash
pytest tests/test_knowledge_queue.py -v
```

Expected: FAIL because queue APIs do not exist.

**Step 3: Implement queue state primitives**

Add data structures and store methods for:

- `CaptureJob`
- job metadata serialization
- queue directories bootstrap
- enqueue/load/update operations
- processing/failed/retracted state files or indexes

Do not add worker logic yet.

**Step 4: Run queue and store tests**

Run:

```bash
pytest tests/test_knowledge_queue.py tests/test_knowledge_store.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_knowledge_queue.py nanobot/knowledge/models.py nanobot/knowledge/store.py
git commit -m "feat: add local capture queue state"
```

### Task 4: Convert intake service from synchronous routing to enqueue-only

**Files:**
- Modify: `nanobot/knowledge/service.py`
- Modify: `nanobot/knowledge/models.py`
- Test: `tests/test_knowledge_service.py`

**Step 1: Write failing tests for enqueue-only capture**

Add tests asserting that:

- `capture_text()` returns `queued`
- no canonical writes happen during the request
- `capture_file()` stages the attachment and returns a `capture_id`

Example:

```python
async def test_capture_text_enqueues_without_applying_decision(tmp_path: Path):
    service = KnowledgeIntakeService.for_testing(tmp_path, router=FakeRouter())
    result = await service.capture_text("front tire pressure 35", user_hint="bike")
    assert result.status == "queued"
    assert result.capture_id
    assert not any((tmp_path / "entities").glob("**/*"))
```

**Step 2: Run the service test**

Run:

```bash
pytest tests/test_knowledge_service.py -k enqueue -v
```

Expected: FAIL because service still routes synchronously.

**Step 3: Implement enqueue-only intake**

Refactor `KnowledgeIntakeService` so capture methods:

- save the staged payload
- enqueue a job
- return `capture_id`, `status`, and runtime path/reference
- do not call `router.route()` or `store.apply_decision()` inline

**Step 4: Run service tests**

Run:

```bash
pytest tests/test_knowledge_service.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_knowledge_service.py nanobot/knowledge/service.py nanobot/knowledge/models.py
git commit -m "feat: enqueue captures instead of routing inline"
```

### Task 5: Add a background queue worker and job processor

**Files:**
- Create: `nanobot/knowledge/worker.py`
- Modify: `nanobot/knowledge/store.py`
- Modify: `nanobot/knowledge/router.py`
- Create: `tests/test_knowledge_worker.py`

**Step 1: Write failing worker tests**

Cover:

- worker picks a queued job and marks it `processing`
- successful processing transitions to `completed`
- failed processing transitions to `failed`
- `needs_input` is preserved when the router returns a follow-up

Example:

```python
async def test_worker_processes_queued_text_job(tmp_path: Path):
    store = KnowledgeStore(tmp_path, KnowledgeConfig())
    job = store.enqueue_text_capture("This is my bike insurer", source="telegram")
    worker = KnowledgeWorker(tmp_path, router=FakeRouter())
    await worker.process_once()
    processed = store.load_job(job.capture_id)
    assert processed.status == "completed"
```

**Step 2: Run the worker test**

Run:

```bash
pytest tests/test_knowledge_worker.py -v
```

Expected: FAIL because worker does not exist.

**Step 3: Implement the worker**

Add a worker that:

- scans queued jobs
- atomically claims one job into `processing`
- reconstructs the staged `InboxItem`
- calls the router
- delegates canonical/archive writes to store methods
- records completion metadata, follow-up, or failure details

Keep the worker independently callable so the gateway and tests can both use it.

**Step 4: Run worker tests**

Run:

```bash
pytest tests/test_knowledge_worker.py tests/test_knowledge_service.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_knowledge_worker.py nanobot/knowledge/worker.py nanobot/knowledge/store.py nanobot/knowledge/router.py
git commit -m "feat: process queued captures in background"
```

### Task 6: Write canonical outputs into Mehr and preserved originals into Nanobot Archive

**Files:**
- Modify: `nanobot/knowledge/store.py`
- Create: `tests/test_knowledge_canonical_write.py`

**Step 1: Write failing canonical write tests**

Cover:

- canonical note updates go under `Mehr`, not `~/.nanobot/workspace/entities`
- preserved originals go under `Nanobot Archive`
- canonical notes link to the archive path when the original is retained

Example:

```python
def test_apply_decision_writes_to_mehr_and_archive(tmp_path: Path):
    config = KnowledgeConfig(
        canonical_root=tmp_path / "Mehr",
        archive_root=tmp_path / "Nanobot Archive",
    )
    store = KnowledgeStore(tmp_path / "workspace", config)
    decision = make_decision_for_receipt()
    store.apply_processed_job(job, decision, artifact_path=tmp_path / "receipt.pdf")
    assert (tmp_path / "Mehr").exists()
    assert any((tmp_path / "Nanobot Archive").glob("**/receipt.pdf"))
```

**Step 2: Run canonical write tests**

Run:

```bash
pytest tests/test_knowledge_canonical_write.py -v
```

Expected: FAIL because store still targets workspace entities/artifacts.

**Step 3: Implement Mehr/archive writers**

Refactor store write methods so processed jobs:

- update canonical files in `config.canonical_root`
- preserve originals in `config.archive_root` only when required
- record canonical and archive paths on the job result
- stop presenting `workspace/inbox` as the user-facing destination

**Step 4: Run storage tests**

Run:

```bash
pytest tests/test_knowledge_canonical_write.py tests/test_knowledge_store.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_knowledge_canonical_write.py nanobot/knowledge/store.py
git commit -m "feat: write canonical memory into Mehr"
```

### Task 7: Add retract/delete support with rollback

**Files:**
- Modify: `nanobot/knowledge/store.py`
- Modify: `nanobot/knowledge/service.py`
- Create: `tests/test_knowledge_retract.py`

**Step 1: Write failing retract tests**

Cover:

- retract removes canonical writes from `Mehr`
- retract removes preserved originals from `Nanobot Archive`
- retract marks a local tombstone under runtime state

Example:

```python
def test_retract_capture_removes_canonical_and_archive_outputs(tmp_path: Path):
    service = seeded_completed_capture_service(tmp_path)
    result = service.retract_capture("cap_123")
    assert result.status == "retracted"
    assert not list((tmp_path / "Mehr").glob("**/receipt*"))
    assert not list((tmp_path / "Nanobot Archive").glob("**/receipt*"))
```

**Step 2: Run retract tests**

Run:

```bash
pytest tests/test_knowledge_retract.py -v
```

Expected: FAIL because retract support does not exist.

**Step 3: Implement retract workflow**

Add:

- local tombstone metadata
- rollback of linked canonical/archive paths
- service API for `retract_capture(capture_id)`

Do not implement app UI yet.

**Step 4: Run retract tests**

Run:

```bash
pytest tests/test_knowledge_retract.py tests/test_knowledge_worker.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_knowledge_retract.py nanobot/knowledge/store.py nanobot/knowledge/service.py
git commit -m "feat: support capture retraction"
```

### Task 8: Expose worker processing and job status through the gateway and capture endpoints

**Files:**
- Modify: `nanobot/cli/commands.py`
- Modify: `nanobot/knowledge/native_inbox.py`
- Modify: `nanobot/knowledge/web_inbox.py`
- Modify: `nanobot/agent/loop.py`
- Modify: `tests/test_commands.py`
- Modify: `tests/test_knowledge_native_inbox.py`
- Modify: `tests/test_knowledge_web_inbox.py`
- Modify: `tests/test_capture_mode.py`

**Step 1: Write failing integration tests**

Add coverage for:

- gateway starts the background worker
- native/web endpoints return queued job metadata
- chat `/capture` responses include `capture_id` and queued status

Example:

```python
def test_native_inbox_returns_queued_capture_metadata(client):
    response = client.post("/capture", json={"content_text": "bike insurer"})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["capture_id"]
```

**Step 2: Run the focused integration tests**

Run:

```bash
pytest tests/test_commands.py tests/test_knowledge_native_inbox.py tests/test_knowledge_web_inbox.py tests/test_capture_mode.py -v
```

Expected: FAIL because endpoints still return synchronous results.

**Step 3: Implement worker wiring and queue-aware responses**

Update gateway startup and capture endpoints so they:

- start the queue worker loop
- return `202 Accepted` style queued results where appropriate
- expose job status lookups for the Mac app and Share extension
- preserve source-channel metadata for Telegram and WhatsApp jobs

**Step 4: Run the integration tests**

Run:

```bash
pytest tests/test_commands.py tests/test_knowledge_native_inbox.py tests/test_knowledge_web_inbox.py tests/test_capture_mode.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_commands.py tests/test_knowledge_native_inbox.py tests/test_knowledge_web_inbox.py tests/test_capture_mode.py nanobot/cli/commands.py nanobot/knowledge/native_inbox.py nanobot/knowledge/web_inbox.py nanobot/agent/loop.py
git commit -m "feat: expose queued capture status across channels"
```

### Task 9: Add recent-capture status APIs and loading feedback support for the Mac app

**Files:**
- Modify: `nanobot/knowledge/native_inbox.py`
- Create: `tests/test_knowledge_native_status.py`
- Modify: `macos/NanobotCapture/NanobotCapture/Client/NativeCaptureClient.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/NativeCaptureClientTests.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`

**Step 1: Write failing backend status tests**

Add tests for:

- `GET /captures/recent`
- `GET /captures/<capture_id>`
- queued/processing/completed payload shape

**Step 2: Run backend status tests**

Run:

```bash
pytest tests/test_knowledge_native_status.py -v
```

Expected: FAIL because status APIs do not exist.

**Step 3: Write failing Mac app tests**

Add app tests covering:

- visible loading state while a submission is in flight
- recent captures list renders source/status
- completed item shows the canonical `Mehr` destination, not the staging path

**Step 4: Run the focused app tests**

Run:

```bash
cd macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/NativeCaptureClientTests -only-testing:NanobotCaptureTests/SmokeTests
```

Expected: FAIL because the app does not yet support these states.

**Step 5: Implement backend status APIs and app loading UI**

Add:

- native endpoint(s) to fetch recent jobs and individual status
- app spinner/progress state during queue submission
- recent captures panel/list
- canonical destination rendering

Preserve the current responsive composer layout.

**Step 6: Run backend and app tests**

Run:

```bash
pytest tests/test_knowledge_native_status.py -v
cd macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS.

**Step 7: Commit**

```bash
git add tests/test_knowledge_native_status.py nanobot/knowledge/native_inbox.py macos/NanobotCapture/NanobotCapture/Client/NativeCaptureClient.swift macos/NanobotCapture/NanobotCapture/App/AppState.swift macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift macos/NanobotCapture/NanobotCaptureTests/NativeCaptureClientTests.swift macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "feat: add queued capture progress to mac app"
```

### Task 10: Add retract/retry controls to the Mac app and share success UI

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/Client/NativeCaptureClient.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureShareExtension/ShareView.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/ShareExtensionModelTests.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`

**Step 1: Write failing UI tests**

Cover:

- retract action calls the new API and updates the item state
- retry action is available for failed jobs
- share extension shows explicit queued/success UI after submission

**Step 2: Run the focused UI tests**

Run:

```bash
cd macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/ShareExtensionModelTests -only-testing:NanobotCaptureTests/SmokeTests
```

Expected: FAIL because retract/retry/success states do not exist yet.

**Step 3: Implement the controls**

Add:

- app actions for `Retry` and `Retract`
- share extension success confirmation with canonical destination summary
- recent captures status refresh after actions

**Step 4: Run the UI tests**

Run:

```bash
cd macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS.

**Step 5: Commit**

```bash
git add macos/NanobotCapture/NanobotCapture/Client/NativeCaptureClient.swift macos/NanobotCapture/NanobotCapture/App/AppState.swift macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift macos/NanobotCapture/NanobotCaptureShareExtension/ShareView.swift macos/NanobotCapture/NanobotCaptureTests/ShareExtensionModelTests.swift macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "feat: add capture recovery controls"
```

### Task 11: Migrate docs and user-facing explanations to the queue model

**Files:**
- Modify: `README.md`
- Modify: `docs/hybrid-knowledge-capture.md`
- Modify: `macos/NanobotCapture/README.md`

**Step 1: Write the docs changes**

Update user-facing docs so they explain:

- `Mehr` is canonical memory
- `Drop to Nanobot` is temporary intake
- `Nanobot Archive` holds preserved originals
- the app shows queued/processing/completed/retracted states
- deleting a capture should be done through retract, not manual file deletion

**Step 2: Run a docs sanity check**

Run:

```bash
rg -n "workspace/inbox|entities/|saved record here" README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
```

Expected: no stale guidance that presents the runtime inbox as canonical memory.

**Step 3: Commit**

```bash
git add README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
git commit -m "docs: describe queued Mehr capture model"
```

### Task 12: Run end-to-end verification

**Files:**
- Test: `tests/test_knowledge_config.py`
- Test: `tests/test_knowledge_queue.py`
- Test: `tests/test_knowledge_service.py`
- Test: `tests/test_knowledge_worker.py`
- Test: `tests/test_knowledge_canonical_write.py`
- Test: `tests/test_knowledge_retract.py`
- Test: `tests/test_knowledge_native_inbox.py`
- Test: `tests/test_knowledge_native_status.py`
- Test: `tests/test_knowledge_web_inbox.py`
- Test: `tests/test_commands.py`
- Test: `tests/test_capture_mode.py`
- Test: `macos/NanobotCapture/NanobotCaptureTests/*`

**Step 1: Run the Python verification suite**

Run:

```bash
pytest tests/test_knowledge_config.py tests/test_knowledge_queue.py tests/test_knowledge_service.py tests/test_knowledge_worker.py tests/test_knowledge_canonical_write.py tests/test_knowledge_retract.py tests/test_knowledge_native_inbox.py tests/test_knowledge_native_status.py tests/test_knowledge_web_inbox.py tests/test_commands.py tests/test_capture_mode.py -v
```

Expected: PASS.

**Step 2: Run the macOS verification suite**

Run:

```bash
cd macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS.

**Step 3: Manual smoke test**

Run the gateway and verify these behaviors manually:

1. Paste a screenshot into the Mac app and confirm it appears in recent captures.
2. Wait for processing and confirm the completed item shows a canonical path under `Mehr`.
3. Trigger a capture from Telegram or `/capture` and confirm the same item appears in recent captures with `source_channel=telegram`.
4. Retract one capture and confirm the canonical output and any archived original are removed.

**Step 4: Commit**

No new commit unless manual-smoke-only fixes are needed.

