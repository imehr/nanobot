# macOS Native Capture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-only macOS-native capture layer for nanobot with a menu bar app, full app window, and native Share extension that submits into the existing hybrid knowledge pipeline.

**Architecture:** Add a dedicated loopback-only native capture endpoint on the Python side, then build a Swift/SwiftUI macOS app bundle that submits captures through that endpoint. Keep the native layer capture-only and separate from the existing LAN/browser inbox.

**Tech Stack:** Python, Typer, existing nanobot knowledge services, Swift, SwiftUI, Xcode project targets, macOS Share Extensions, Keychain Services

---

### Task 1: Add native capture config schema

**Files:**
- Modify: `nanobot/config/schema.py`
- Test: `tests/test_knowledge_config.py`

**Step 1: Write the failing test**

Add a config test that expects a `knowledge.nativeCapture` section with:

- `enabled`
- `bind`
- `port`
- `authToken`

**Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/pytest tests/test_knowledge_config.py -v
```

Expected: FAIL because `nativeCapture` is not defined in the schema.

**Step 3: Write minimal implementation**

Add a new config model in `nanobot/config/schema.py` for the native local endpoint and attach it under `KnowledgeConfig`.

**Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/pytest tests/test_knowledge_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/config/schema.py tests/test_knowledge_config.py
git commit -m "feat: add native capture config"
```

### Task 2: Build the local-native capture service

**Files:**
- Create: `nanobot/knowledge/native_inbox.py`
- Modify: `nanobot/knowledge/service.py`
- Modify: `nanobot/cli/commands.py`
- Test: `tests/test_knowledge_native_inbox.py`

**Step 1: Write the failing test**

Create tests that verify:

- `GET /health` returns `200`
- `POST /capture` rejects missing or wrong token
- `POST /capture` accepts text payloads with correct token
- file uploads are preserved before routing

**Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/pytest tests/test_knowledge_native_inbox.py -v
```

Expected: FAIL because the server module does not exist.

**Step 3: Write minimal implementation**

Create `nanobot/knowledge/native_inbox.py` to expose a loopback-only HTTP service with:

- `GET /health`
- `POST /capture`

Require a bearer token on `POST /capture`.

Reuse the current `KnowledgeIntakeService` for persistence and routing.

Wire the service into `nanobot/cli/commands.py` so `gateway` starts it when enabled.

**Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/pytest tests/test_knowledge_native_inbox.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/native_inbox.py nanobot/knowledge/service.py nanobot/cli/commands.py tests/test_knowledge_native_inbox.py
git commit -m "feat: add native mac capture endpoint"
```

### Task 3: Add end-to-end Python verification for native capture wiring

**Files:**
- Modify: `tests/test_commands.py`
- Modify: `tests/test_capture_mode.py`

**Step 1: Write the failing test**

Add tests that verify:

- gateway startup includes the native endpoint when configured
- native capture remains separate from the LAN/browser inbox
- no read/list routes are present

**Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/pytest tests/test_commands.py tests/test_capture_mode.py -v
```

Expected: FAIL because the gateway output and service wiring do not yet include the native endpoint.

**Step 3: Write minimal implementation**

Adjust gateway wiring and any related output so the new native endpoint is surfaced clearly but remains distinct from the LAN inbox.

**Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/pytest tests/test_commands.py tests/test_capture_mode.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/cli/commands.py tests/test_commands.py tests/test_capture_mode.py
git commit -m "test: verify native capture gateway wiring"
```

### Task 4: Scaffold the macOS app project

**Files:**
- Create: `macos/NanobotCapture/NanobotCapture.xcodeproj/project.pbxproj`
- Create: `macos/NanobotCapture/NanobotCapture/App/NanobotCaptureApp.swift`
- Create: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Create: `macos/NanobotCapture/NanobotCapture/Resources/Assets.xcassets/Contents.json`
- Create: `macos/NanobotCapture/README.md`

**Step 1: Write the failing test**

Create a lightweight project smoke check by adding a command in `macos/NanobotCapture/README.md` that expects the project to open and build in Xcode.

For code tests, add a placeholder Swift test target in a later task before adding behavior.

**Step 2: Run project validation to verify missing files**

Run:

```bash
test -f macos/NanobotCapture/NanobotCapture.xcodeproj/project.pbxproj
```

Expected: FAIL

**Step 3: Write minimal implementation**

Scaffold the macOS app project with:

- one app target
- one test target
- one Share extension target placeholder
- SwiftUI app entry point

**Step 4: Run validation**

Run:

```bash
test -f macos/NanobotCapture/NanobotCapture.xcodeproj/project.pbxproj
```

Expected: PASS

**Step 5: Commit**

```bash
git add macos/NanobotCapture
git commit -m "feat: scaffold macos capture app"
```

### Task 5: Implement the shared native submission client

**Files:**
- Create: `macos/NanobotCapture/NanobotCapture/Client/NativeCaptureClient.swift`
- Create: `macos/NanobotCapture/NanobotCapture/Client/CapturePayload.swift`
- Create: `macos/NanobotCapture/NanobotCapture/Client/KeychainStore.swift`
- Create: `macos/NanobotCapture/NanobotCaptureTests/NativeCaptureClientTests.swift`

**Step 1: Write the failing test**

Add Swift tests that verify:

- payload builds for text-only submissions
- payload builds for file-backed submissions
- bearer token is attached to requests

**Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: FAIL because the client and tests do not exist.

**Step 3: Write minimal implementation**

Create a small client that:

- submits multipart or JSON payloads
- reads/stores the local token
- exposes a simple async submit API for the app and Share extension

**Step 4: Run test to verify it passes**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS

**Step 5: Commit**

```bash
git add macos/NanobotCapture/NanobotCapture macos/NanobotCapture/NanobotCaptureTests
git commit -m "feat: add native capture client"
```

### Task 6: Build the full app window

**Files:**
- Create: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- Create: `macos/NanobotCapture/NanobotCapture/UI/FileDropZone.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift`

**Step 1: Write the failing test**

Add view-model tests for:

- note and hint handling
- multi-file selection state
- submit button enabled/disabled rules
- result message mapping

**Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: FAIL because the capture window state and UI do not exist.

**Step 3: Write minimal implementation**

Create the main SwiftUI capture form with:

- note field
- hint field
- drag-drop area
- file picker
- submit button
- result panel

**Step 4: Run test to verify it passes**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS

**Step 5: Commit**

```bash
git add macos/NanobotCapture/NanobotCapture
git commit -m "feat: add macos capture window"
```

### Task 7: Build the menu bar quick capture flow

**Files:**
- Create: `macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/App/NanobotCaptureApp.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/MenuBarCaptureTests.swift`

**Step 1: Write the failing test**

Add tests for menu bar quick capture state:

- paste text flow
- clipboard action
- result rendering

**Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: FAIL because the menu bar UI does not exist.

**Step 3: Write minimal implementation**

Add a `MenuBarExtra`-based quick capture panel with:

- compact note field
- hint field
- clipboard import
- open full window button
- submit and result display

**Step 4: Run test to verify it passes**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS

**Step 5: Commit**

```bash
git add macos/NanobotCapture/NanobotCapture
git commit -m "feat: add macos menu bar capture"
```

### Task 8: Add the Share extension

**Files:**
- Create: `macos/NanobotCapture/NanobotCaptureShareExtension/ShareViewController.swift`
- Create: `macos/NanobotCapture/NanobotCaptureShareExtension/ShareView.swift`
- Create: `macos/NanobotCapture/NanobotCaptureShareExtension/ExtensionPayloadExtractor.swift`
- Modify: `macos/NanobotCapture/NanobotCapture.xcodeproj/project.pbxproj`
- Test: `macos/NanobotCapture/NanobotCaptureTests/ExtensionPayloadExtractorTests.swift`

**Step 1: Write the failing test**

Add extractor tests for:

- URL payloads
- text payloads
- file URL payloads
- image payloads

**Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: FAIL because the extension target and extractor do not exist.

**Step 3: Write minimal implementation**

Create the Share extension that:

- receives host app items
- extracts the supported payload
- shows note/hint fields
- submits through the shared native client

**Step 4: Run test to verify it passes**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS

**Step 5: Commit**

```bash
git add macos/NanobotCapture
git commit -m "feat: add macos share extension"
```

### Task 9: Document setup, install, and security boundaries

**Files:**
- Modify: `README.md`
- Modify: `docs/hybrid-knowledge-capture.md`
- Modify: `macos/NanobotCapture/README.md`

**Step 1: Write the failing doc check**

Create a checklist of missing user-facing items:

- how to build the app
- how to launch it
- how to enable the Share extension
- what the native endpoint can and cannot do

**Step 2: Verify docs are incomplete**

Run:

```bash
rg -n "Share extension|menu bar app|NanobotCapture" README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
```

Expected: missing or incomplete output

**Step 3: Write minimal documentation**

Document:

- local-only security boundary
- build/install steps
- how to use the menu bar app
- how to use the Share extension
- how this differs from the LAN/browser inbox

**Step 4: Verify docs**

Run:

```bash
rg -n "Share extension|menu bar app|NanobotCapture" README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
```

Expected: matching documentation entries

**Step 5: Commit**

```bash
git add README.md docs/hybrid-knowledge-capture.md macos/NanobotCapture/README.md
git commit -m "docs: add macos native capture usage"
```

### Task 10: Full verification

**Files:**
- Modify: none

**Step 1: Run Python tests**

Run:

```bash
./.venv/bin/pytest tests/test_knowledge_config.py tests/test_knowledge_native_inbox.py tests/test_commands.py tests/test_capture_mode.py -v
```

Expected: PASS

**Step 2: Run macOS tests**

Run:

```bash
xcodebuild test -project macos/NanobotCapture/NanobotCapture.xcodeproj -scheme NanobotCapture -destination 'platform=macOS'
```

Expected: PASS

**Step 3: Manual end-to-end verification**

Validate:

- menu bar text capture works
- app window file capture works
- Finder Share -> Nanobot works
- Safari Share -> Nanobot works
- Preview Share -> Nanobot works
- native endpoint rejects wrong token
- LAN/browser inbox still works independently

**Step 4: Commit final integration check**

```bash
git status
```

Expected: clean or only intentional changes

