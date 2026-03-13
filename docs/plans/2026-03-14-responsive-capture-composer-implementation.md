# Responsive Capture Composer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the macOS capture window into a responsive composer and make screenshot paste reliably attach and submit from the installed app.

**Architecture:** Keep the current loopback native capture backend and replace the brittle single-column SwiftUI window with a width-aware composer. Introduce an attachment view model that can represent screenshots and files cleanly, route clipboard images into that model, and keep the bottom action bar fixed while the body adapts to window size.

**Tech Stack:** SwiftUI, AppKit, XCTest, Xcode/xcodebuild, existing Python native capture endpoint

---

### Task 1: Lock the failing screenshot-paste behavior in tests

**Files:**
- Modify: `macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`

**Step 1: Write the failing tests**

Add tests that require:
- pasted image providers create a visible attachment model entry
- the attachment model exposes image kind/thumbnail metadata
- responsive layout constants define both wide and compact breakpoints

**Step 2: Run test to verify it fails**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/CaptureWindowViewModelTests -only-testing:NanobotCaptureTests/SmokeTests`

Expected: FAIL because the current model only stores `[URL]` and has no responsive layout metadata.

**Step 3: Write minimal implementation**

Do not implement the full UI yet. Add only the minimum model/layout scaffolding needed to make the tests compile once the next tasks land.

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "test: lock responsive capture composer behavior"
```

### Task 2: Introduce an attachment model for the app window

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Create: `macos/NanobotCapture/NanobotCapture/UI/CaptureAttachment.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift`

**Step 1: Write the failing test**

Add a test that requires:
- image clipboard payloads become attachment items
- attachments can be removed individually
- file-backed attachments still submit through file URLs

**Step 2: Run test to verify it fails**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/CaptureWindowViewModelTests`

Expected: FAIL because the window model cannot express attachment cards or removal.

**Step 3: Write minimal implementation**

Implement:
- `CaptureAttachment` with id, file URL, display name, kind, optional thumbnail
- `CaptureWindowViewModel.attachments`
- helpers to add/remove attachments
- submission path derived from `attachments.map(\\.fileURL)`

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/App/AppState.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/UI/CaptureAttachment.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift
git commit -m "feat: add capture attachment model"
```

### Task 3: Fix clipboard and paste handling at the root cause

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureShareExtension/ExtensionPayloadExtractor.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift`

**Step 1: Write the failing test**

Add tests that require:
- `captureClipboard()` with an image creates an attachment item and updates status to `Screenshot added`
- `handlePasteProviders()` with image providers adds an attachment even when no note text exists

**Step 2: Run test to verify it fails**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/CaptureWindowViewModelTests`

Expected: FAIL because the current code path is not reliably reflected in the visible attachment state.

**Step 3: Write minimal implementation**

Implement:
- one normalization path for clipboard image/file/text payloads
- direct attachment creation for screenshots
- specific status messages for screenshot vs generic paste

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/App/AppState.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureShareExtension/ExtensionPayloadExtractor.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift
git commit -m "fix: make screenshot paste attach reliably"
```

### Task 4: Replace the current window with a responsive composer

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/UI/FileDropZone.swift`
- Create: `macos/NanobotCapture/NanobotCapture/UI/CaptureAttachmentPanel.swift`
- Create: `macos/NanobotCapture/NanobotCapture/UI/CaptureAttachmentCard.swift`
- Test: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`

**Step 1: Write the failing test**

Add a layout-oriented test that requires:
- a wide mode breakpoint
- a compact mode breakpoint
- a fixed bottom action bar
- a non-scrollable header region

**Step 2: Run test to verify it fails**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/SmokeTests`

Expected: FAIL because the current window has only the old single-column layout constants.

**Step 3: Write minimal implementation**

Implement:
- width-aware layout switching
- persistent header outside the scrollable body
- left/right split for wide windows
- stacked mode for compact windows
- attachment panel with thumbnail/file cards
- remove actions per attachment

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/UI/FileDropZone.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/UI/CaptureAttachmentPanel.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/UI/CaptureAttachmentCard.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "feat: redesign capture window as responsive composer"
```

### Task 5: Keep submission and result handling correct in the new UI

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/Client/CapturePayload.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/NativeCaptureClientTests.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift`

**Step 1: Write the failing test**

Add tests that require:
- capture stays enabled with image attachments and no text
- result state stays attached to the saved record path
- failed submissions do not clear attachments

**Step 2: Run test to verify it fails**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/CaptureWindowViewModelTests -only-testing:NanobotCaptureTests/NativeCaptureClientTests`

Expected: FAIL if the new attachment model is not fully wired into submission and error handling.

**Step 3: Write minimal implementation**

Implement:
- attachment-backed submit path
- explicit failure messages
- preserve attachments on failed submit

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/App/AppState.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/Client/CapturePayload.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/NativeCaptureClientTests.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/CaptureWindowViewModelTests.swift
git commit -m "fix: keep capture submission stable with attachments"
```

### Task 6: Update docs for the real screenshot workflow

**Files:**
- Modify: `docs/hybrid-knowledge-capture.md`
- Modify: `macos/NanobotCapture/README.md`

**Step 1: Write the failing doc expectation**

Document the actual supported flow:
- take screenshot to clipboard
- paste into the app
- see thumbnail in the window
- submit and verify saved record path

**Step 2: Run doc sanity check**

Read both files and verify they no longer describe unsupported preview/modal behavior.

Expected: The current docs are incomplete relative to the redesigned UX.

**Step 3: Write minimal implementation**

Update the docs to match the shipped UI and troubleshooting guidance.

**Step 4: Re-read docs to verify**

Run:

```bash
sed -n '1,260p' /Users/mehranmozaffari/Documents/github/nanobot/docs/hybrid-knowledge-capture.md
sed -n '1,220p' /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/README.md
```

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/docs/hybrid-knowledge-capture.md /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/README.md
git commit -m "docs: update responsive capture composer workflow"
```

### Task 7: Rebuild, reinstall, and verify on the installed Mac app

**Files:**
- Built app: `/Users/mehranmozaffari/Applications/NanobotCapture.app`

**Step 1: Run the full macOS test suite**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'`

Expected: PASS with all tests green.

**Step 2: Build the app**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild build -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -configuration Debug -destination 'platform=macOS'`

Expected: `BUILD SUCCEEDED`

**Step 3: Reinstall the app**

Run:

```bash
ditto /Users/mehranmozaffari/Library/Developer/Xcode/DerivedData/NanobotCapture-gwxbatqzmvnlqveaygdajlvbwdtg/Build/Products/Debug/NanobotCapture.app /Users/mehranmozaffari/Applications/NanobotCapture.app
```

**Step 4: Relaunch the app**

Run:

```bash
osascript -e 'tell application "NanobotCapture" to quit'
open /Users/mehranmozaffari/Applications/NanobotCapture.app
```

**Step 5: Manual verification**

Verify on this Mac:
- window opens with visible header and responsive body
- screenshot paste produces an attachment thumbnail and non-zero count
- `Capture to Nanobot` succeeds with the pasted screenshot
- result links to a saved inbox record

**Step 6: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
git commit -m "feat: ship responsive capture composer"
```
