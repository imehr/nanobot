# Project Memory Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a project-memory layer that stores concise project summaries, decisions, timelines, and feature notes in `Mehr/Projects/<project>/...`, while keeping detailed technical truth in each repository.

**Architecture:** Extend the queued capture pipeline so project-related captures can write canonical summaries into `Mehr/Projects`. Keep project memory as a new routing target, not a separate system. Surface resulting project-memory writes through the capture app, share extension, and channel responses.

**Tech Stack:** Python, Pydantic, SwiftUI, XcodeGen, pytest, xcodebuild

---

### Task 1: Define project-memory data model and config mapping

**Files:**
- Modify: `nanobot/config/schema.py`
- Modify: `nanobot/knowledge/models.py`
- Test: `tests/test_knowledge_config.py`

**Step 1: Write the failing test**

Add coverage that project-memory settings resolve to:
- `Mehr/Projects`
- project memory enable flag or defaults
- a typed capture output shape for project-memory destinations

**Step 2: Run test to verify it fails**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_knowledge_config.py -v`
Expected: FAIL because the config/model fields do not exist yet.

**Step 3: Write minimal implementation**

Add:
- project-memory root/defaults under knowledge config
- model fields for project-memory outputs on queued job status or canonical result types

**Step 4: Run test to verify it passes**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_knowledge_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/config/schema.py nanobot/knowledge/models.py tests/test_knowledge_config.py
git commit -m "feat: add project memory config"
```

### Task 2: Add project-memory store helpers

**Files:**
- Modify: `nanobot/knowledge/store.py`
- Test: `tests/test_knowledge_store.py`
- Create: `tests/test_project_memory_store.py`

**Step 1: Write the failing test**

Add tests for store helpers that can:
- create `Mehr/Projects/<project>/`
- seed `index.md`, `decisions.md`, `timeline.md`, `links.md`
- create `features/<slug>.md` lazily

**Step 2: Run test to verify it fails**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_project_memory_store.py -v`
Expected: FAIL because the helpers do not exist.

**Step 3: Write minimal implementation**

Implement:
- project folder path helpers
- Markdown file bootstrap
- append/update helpers for timeline, decisions, and feature summaries

**Step 4: Run test to verify it passes**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_project_memory_store.py tests/test_knowledge_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/store.py tests/test_project_memory_store.py tests/test_knowledge_store.py
git commit -m "feat: add project memory store helpers"
```

### Task 3: Extend routing output for project memory

**Files:**
- Modify: `nanobot/knowledge/router.py`
- Modify: `nanobot/knowledge/models.py`
- Create: `tests/test_project_memory_router.py`

**Step 1: Write the failing test**

Add tests for routing decisions such as:
- significant project/feature note -> project memory write
- temporary debugging note -> no project memory write
- major architecture decision -> update `decisions.md` and `timeline.md`

**Step 2: Run test to verify it fails**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_project_memory_router.py -v`
Expected: FAIL because router output cannot express project-memory actions yet.

**Step 3: Write minimal implementation**

Add routing concepts like:
- `project_name`
- `project_memory_actions`
- target file types: `index`, `decisions`, `timeline`, `feature`

Keep rules conservative so only meaningful work creates project-memory entries.

**Step 4: Run test to verify it passes**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_project_memory_router.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/router.py nanobot/knowledge/models.py tests/test_project_memory_router.py
git commit -m "feat: route significant captures into project memory"
```

### Task 4: Write project memory during queued processing

**Files:**
- Modify: `nanobot/knowledge/worker.py`
- Modify: `nanobot/knowledge/store.py`
- Create: `tests/test_project_memory_worker.py`

**Step 1: Write the failing test**

Add an end-to-end worker test showing:
- a queued project-related capture is processed
- canonical outputs go to `Mehr`
- project memory gets updated under `Mehr/Projects/<project>/...`
- job status stores project-memory output paths

**Step 2: Run test to verify it fails**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_project_memory_worker.py -v`
Expected: FAIL because worker does not write project memory yet.

**Step 3: Write minimal implementation**

Update worker flow to:
- apply normal canonical writes
- apply project-memory writes if router requests them
- record those paths on the job

**Step 4: Run test to verify it passes**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_project_memory_worker.py tests/test_knowledge_worker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/worker.py nanobot/knowledge/store.py tests/test_project_memory_worker.py tests/test_knowledge_worker.py
git commit -m "feat: persist project memory from queued captures"
```

### Task 5: Expose project-memory outputs through status APIs

**Files:**
- Modify: `nanobot/knowledge/native_inbox.py`
- Modify: `nanobot/knowledge/web_inbox.py`
- Modify: `nanobot/cli/commands.py`
- Test: `tests/test_knowledge_native_status.py`
- Test: `tests/test_knowledge_web_inbox.py`
- Test: `tests/test_commands.py`

**Step 1: Write the failing test**

Add assertions that status payloads include project-memory paths when present.

**Step 2: Run test to verify it fails**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_knowledge_native_status.py tests/test_knowledge_web_inbox.py tests/test_commands.py -v`
Expected: FAIL because project-memory outputs are not exposed.

**Step 3: Write minimal implementation**

Return project-memory outputs in:
- native capture status payloads
- recent capture list payloads
- CLI render output

**Step 4: Run test to verify it passes**

Run: `/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_knowledge_native_status.py tests/test_knowledge_web_inbox.py tests/test_commands.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/native_inbox.py nanobot/knowledge/web_inbox.py nanobot/cli/commands.py tests/test_knowledge_native_status.py tests/test_knowledge_web_inbox.py tests/test_commands.py
git commit -m "feat: expose project memory in capture status"
```

### Task 6: Update Mac app result and recent-capture UI

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/MenuBarCaptureTests.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`

**Step 1: Write the failing test**

Add or update tests so the app can:
- display project-memory paths in results
- show a project-memory indicator in recent captures
- reveal the primary project-memory path when that is the most useful destination

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: FAIL because result/status rendering does not include project-memory outputs.

**Step 3: Write minimal implementation**

Update app-state description helpers and recent-capture cards so project memory is visible and revealable.

**Step 4: Run test to verify it passes**

Run the same `xcodebuild test` command.
Expected: PASS

**Step 5: Commit**

```bash
git add macos/NanobotCapture/NanobotCapture/App/AppState.swift macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift macos/NanobotCapture/NanobotCaptureTests/MenuBarCaptureTests.swift macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "feat: surface project memory in mac capture ui"
```

### Task 7: Seed Nanobot project memory from current work

**Files:**
- Create: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot/index.md`
- Create: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot/decisions.md`
- Create: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot/timeline.md`
- Create: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot/features/macos-capture.md`
- Create: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot/features/queued-mehr-memory.md`
- Create: `/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot/links.md`

**Step 1: Write the content template**

Prepare short, linked summaries for:
- project purpose
- major capture architecture decisions
- Mac app and share extension work
- queued processing and canonical Mehr memory

**Step 2: Verify content placement**

Run:

```bash
find "/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot" -maxdepth 2 -type f | sort
```

Expected: all six seed files exist.

**Step 3: Create the seed files**

Write concise summaries only. Do not duplicate the full repo docs.

**Step 4: Manually inspect**

Open the files and confirm:
- they are short
- they link back to repo docs
- they reflect the current Nanobot capture architecture accurately

**Step 5: Commit**

```bash
git add "/Users/mehranmozaffari/Library/Mobile Documents/com~apple~CloudDocs/Mehr/Projects/nanobot"
git commit -m "docs: seed nanobot project memory"
```

### Task 8: Document the project-memory model

**Files:**
- Modify: `docs/hybrid-knowledge-capture.md`
- Modify: `README.md`
- Modify: `macos/NanobotCapture/README.md`

**Step 1: Write the failing doc checklist**

Add a short checklist of what the docs must explain:
- repo docs vs project memory vs archive
- `Mehr/Projects` structure
- when captures update project memory
- where to look for decisions and timelines

**Step 2: Update docs**

Document:
- project-memory purpose
- storage rules
- retrieval behavior
- operational visibility in the app

**Step 3: Verify docs reference correct paths**

Run:

```bash
rg -n "Mehr/Projects|Nanobot Archive|project memory" README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
```

Expected: all docs mention the new model consistently.

**Step 4: Commit**

```bash
git add README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
git commit -m "docs: explain project memory layer"
```

### Task 9: Full verification

**Files:**
- Verify existing and new tests only

**Step 1: Run Python verification**

Run:

```bash
/Users/mehranmozaffari/.nanobot/venv312/bin/python -m pytest tests/test_knowledge_config.py tests/test_knowledge_store.py tests/test_knowledge_service.py tests/test_knowledge_worker.py tests/test_knowledge_canonical_write.py tests/test_knowledge_retract.py tests/test_knowledge_native_inbox.py tests/test_knowledge_native_status.py tests/test_knowledge_web_inbox.py tests/test_commands.py tests/test_capture_mode.py tests/test_project_memory_store.py tests/test_project_memory_router.py tests/test_project_memory_worker.py -v
```

Expected: PASS

**Step 2: Run macOS verification**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS

**Step 3: Manual spot-check**

Verify:
- a meaningful Nanobot-related capture updates `Mehr/Projects/nanobot/...`
- a trivial note does not create project-memory noise
- recent captures show project-memory destinations when applicable

**Step 4: Commit verification-only state if needed**

No code changes expected here. If there are any, commit them explicitly with a narrow message.
