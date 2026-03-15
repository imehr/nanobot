# Web Nanobot Capture Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the local browser capture UI so it matches the current `Nanobot Capture` desktop app in branding, layout, and queue-aware behavior.

**Architecture:** Keep the local Python `web_inbox` service as the delivery mechanism, but replace the old static form with a richer self-contained HTML/CSS/JS app that mirrors the desktop composer. Reuse the existing queue/recent-capture backend state and extend the web endpoints only where needed for browser parity.

**Tech Stack:** Python, built-in HTTP server, inline HTML/CSS/JavaScript, pytest, existing queue/recent-capture services.

---

### Task 1: Lock In The Browser Branding And Page Shape

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/web_inbox.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`

**Step 1: Write the failing test**

Add assertions that the generated inbox page:
- contains `Nanobot Capture`
- no longer contains `nanobot inbox`
- includes recognizable hooks for header, composer, footer, and recent captures

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k branding -v
```

Expected: FAIL because the current page still renders the old branding/layout.

**Step 3: Write minimal implementation**

Update `build_inbox_page()` in `web_inbox.py` to:
- rename the page to `Nanobot Capture`
- adopt the new high-level structure
- add stable DOM hooks/classes for header, body, footer, attachment panel, result panel, and recent captures

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k branding -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_knowledge_web_inbox.py nanobot/knowledge/web_inbox.py
git commit -m "feat: align web capture branding"
```

### Task 2: Add Desktop-Matching Composer Layout

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/web_inbox.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`

**Step 1: Write the failing test**

Add assertions that the page markup includes:
- context section
- hint field
- attachment panel
- action buttons
- persistent footer status/action bar hooks

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k layout -v
```

Expected: FAIL against the old form structure.

**Step 3: Write minimal implementation**

Refactor the page HTML/CSS in `build_inbox_page()` to match the desktop structure:
- persistent header
- responsive two-pane composer
- persistent footer with action button and status line

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k layout -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_knowledge_web_inbox.py nanobot/knowledge/web_inbox.py
git commit -m "feat: add responsive web capture composer"
```

### Task 3: Add Queue-Aware Browser Result And Recent Captures

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/web_inbox.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/native_inbox.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/service.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_native_status.py`

**Step 1: Write the failing test**

Add tests that cover:
- browser result payloads emphasizing canonical destination
- recent-captures/status payload shape expected by the browser UI
- queue status vocabulary (`queued`, `processing`, `completed`, `failed`, `retracted`, `needs_input`)

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py tests/test_knowledge_native_status.py -k "recent or status or destination" -v
```

Expected: FAIL because the browser layer does not yet expose the final shape.

**Step 3: Write minimal implementation**

Add the backend/browser glue needed so the web UI can:
- fetch recent captures
- fetch capture status
- render canonical destination and archive path cleanly
- avoid presenting staging/inbox path as the primary result

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py tests/test_knowledge_native_status.py -k "recent or status or destination" -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_knowledge_web_inbox.py tests/test_knowledge_native_status.py nanobot/knowledge/web_inbox.py nanobot/knowledge/native_inbox.py nanobot/knowledge/service.py
git commit -m "feat: add queue-aware browser capture status"
```

### Task 4: Add Browser Attachment UX And Clipboard Screenshot Paste

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/web_inbox.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`

**Step 1: Write the failing test**

Add tests that assert the generated page includes script hooks/UI markers for:
- drag-drop attachment handling
- paste handling
- clipboard button behavior
- attachment cards/list rendering

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k "clipboard or attachment or paste" -v
```

Expected: FAIL because the current page lacks these behaviors.

**Step 3: Write minimal implementation**

Extend the inline browser JS and markup to:
- track selected attachments client-side
- accept drag-drop file attachments
- attach clipboard screenshots/images via paste event or Clipboard API
- show attachment cards with filename/thumbnail where possible
- keep the `Paste Clipboard` fallback button

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k "clipboard or attachment or paste" -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_knowledge_web_inbox.py nanobot/knowledge/web_inbox.py
git commit -m "feat: add browser clipboard and attachment capture"
```

### Task 5: Add Shared Nanobot Capture Icon And Naming Hooks

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/web_inbox.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/Info.plist`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureShareExtension/Info.plist`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/channels/manager.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`

**Step 1: Write the failing test**

Add assertions that the browser page exposes:
- `Nanobot Capture` name
- icon metadata/hook
- no stale `nanobot inbox` wording

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k "icon or title or capture" -v
```

Expected: FAIL if stale naming remains.

**Step 3: Write minimal implementation**

Wire the red document-memory icon into:
- browser header/icon/fallback metadata
- desktop/share metadata where file-level hooks already exist
- capture-facing naming in relevant channel-facing surfaces if those strings are already templated in code

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py -k "icon or title or capture" -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_knowledge_web_inbox.py nanobot/knowledge/web_inbox.py macos/NanobotCapture/NanobotCapture/Info.plist macos/NanobotCapture/NanobotCaptureShareExtension/Info.plist nanobot/channels/manager.py
git commit -m "feat: unify nanobot capture branding"
```

### Task 6: Verify Full Browser And Capture Slice

**Files:**
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_native_status.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_commands.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/MenuBarCaptureTests.swift`

**Step 1: Run focused Python verification**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest \
  tests/test_knowledge_web_inbox.py \
  tests/test_knowledge_native_status.py \
  tests/test_commands.py -v
```

Expected: PASS

**Step 2: Run focused macOS verification**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/MenuBarCaptureTests
```

Expected: PASS

**Step 3: Manual local smoke check**

Verify:
- `http://127.0.0.1:18791/` shows `Nanobot Capture`
- browser composer matches desktop structure
- paste screenshot into browser UI attaches it visibly
- capture submits and shows queue-aware result

**Step 4: Commit final verification if code changed during polish**

```bash
git add -A
git commit -m "test: verify web nanobot capture alignment"
```

### Task 7: Integrate And Clean Up

**Files:**
- Update: `/Users/mehranmozaffari/Documents/github/nanobot/README.md`
- Update: `/Users/mehranmozaffari/Documents/github/nanobot/docs/hybrid-knowledge-capture.md`

**Step 1: Update docs**

Document:
- browser UI now uses `Nanobot Capture`
- web/browser behavior matches desktop composer
- clipboard screenshot support in browser

**Step 2: Run docs-adjacent verification**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot
PYTHONPATH="$PWD" ./.venv/bin/pytest tests/test_knowledge_web_inbox.py tests/test_commands.py -v
```

Expected: PASS

**Step 3: Commit docs**

```bash
git add README.md docs/hybrid-knowledge-capture.md
git commit -m "docs: update nanobot capture web workflow"
```

**Step 4: Merge back and clean up**

Use the repo’s normal worktree integration flow:
- merge the feature branch into local `main`
- keep `main` clean
- remove the temporary worktree

