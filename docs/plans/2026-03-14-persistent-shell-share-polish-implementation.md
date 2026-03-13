# Persistent Capture Shell And Share Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the macOS capture app a true single-window persistent shell and make the Share extension appear more broadly, including Notes, with an explicit success confirmation state.

**Architecture:** Keep the existing capture backend and responsive composer, but change the app shell to a fixed header/body/footer structure, switch the app scene to a singleton window, broaden the share activation rule, and make the Share extension UI linger in a success state until the user closes it.

**Tech Stack:** SwiftUI, AppKit, XCTest, Xcode/xcodebuild

---

### Task 1: Lock the singleton-window and persistent-shell expectations in tests

**Files:**
- Modify: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`

**Step 1: Write the failing test**

Add assertions for:
- fixed header shell mode
- fixed footer shell mode
- wide/compact responsive layout still intact

**Step 2: Run test to verify it fails**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/SmokeTests`

Expected: FAIL because the current layout does not expose shell invariants explicitly.

**Step 3: Write minimal implementation**

Add the required layout metadata/constants only.

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "test: lock persistent capture shell invariants"
```

### Task 2: Change the app to a real single-window shell

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/App/NanobotCaptureApp.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift`
- Modify: `macos/NanobotCapture/NanobotCapture/App/AppState.swift`

**Step 1: Write the failing test**

Use the shell invariant test plus existing open-window tests to define the expected behavior.

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/MenuBarCaptureTests -only-testing:NanobotCaptureTests/SmokeTests
```

**Step 3: Write minimal implementation**

Implement:
- `Window` scene instead of `WindowGroup`
- fixed header outside the scroll region
- fixed footer outside the scroll region
- only the middle content scrolls
- menu bar open action reuses the singleton window

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/App/NanobotCaptureApp.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/MenuBar/MenuBarCaptureView.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCapture/App/AppState.swift
git commit -m "feat: make capture app a single persistent shell"
```

### Task 3: Broaden share activation and add explicit confirmation UI

**Files:**
- Modify: `macos/NanobotCapture/NanobotCaptureShareExtension/Info.plist`
- Modify: `macos/NanobotCapture/NanobotCaptureShareExtension/ShareView.swift`
- Modify: `macos/NanobotCapture/NanobotCaptureShareExtension/ShareViewController.swift`
- Add/Modify tests: `macos/NanobotCapture/NanobotCaptureTests/MenuBarCaptureTests.swift`

**Step 1: Write the failing test**

Add/adjust tests that require:
- the embedded share manifest to use the broadened activation rule
- share UI to expose a post-submit success state instead of instant dismissal

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/MenuBarCaptureTests
```

**Step 3: Write minimal implementation**

Implement:
- broadened activation rule for Share
- success state in the Share view
- explicit `Done` after success

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureShareExtension/Info.plist /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureShareExtension/ShareView.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureShareExtension/ShareViewController.swift /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/NanobotCaptureTests/MenuBarCaptureTests.swift
git commit -m "feat: polish share activation and confirmation"
```

### Task 4: Clean duplicate extension registrations and reinstall the app

**Files:**
- Installed app: `/Users/mehranmozaffari/Applications/NanobotCapture.app`

**Step 1: Run the full test suite**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'`

Expected: PASS.

**Step 2: Build the app**

Run: `cd /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture && xcodebuild build -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -configuration Debug -destination 'platform=macOS'`

Expected: `BUILD SUCCEEDED`

**Step 3: Clean stale registration noise and reinstall**

Run:

```bash
rm -rf /Users/mehranmozaffari/Library/Developer/Xcode/DerivedData/NanobotCapture-gwxbatqzmvnlqveaygdajlvbwdtg/Build/Products/Debug/NanobotCapture.app
ditto /Users/mehranmozaffari/Library/Developer/Xcode/DerivedData/NanobotCapture-gwxbatqzmvnlqveaygdajlvbwdtg/Build/Products/Debug/NanobotCapture.app /Users/mehranmozaffari/Applications/NanobotCapture.app
pluginkit -r /Users/mehranmozaffari/Applications/NanobotCapture.app/Contents/PlugIns/NanobotCaptureShareExtension.appex
pluginkit -a /Users/mehranmozaffari/Applications/NanobotCapture.app/Contents/PlugIns/NanobotCaptureShareExtension.appex
```

**Step 4: Relaunch**

Run:

```bash
osascript -e 'tell application "NanobotCapture" to quit'
open /Users/mehranmozaffari/Applications/NanobotCapture.app
```

**Step 5: Manual verification**

Verify:
- opening capture repeatedly reuses one window
- header/footer remain visible with many attachments
- Notes Share shows `Nanobot`
- Share submit shows a success state before closing

**Step 6: Commit**

```bash
git add /Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture
git commit -m "feat: finalize capture shell and share flow"
```
