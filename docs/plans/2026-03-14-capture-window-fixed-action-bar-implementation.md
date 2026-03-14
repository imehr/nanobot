# Capture Window Fixed Action Bar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the macOS capture window’s primary action visible without scrolling.

**Architecture:** Move the capture form into a scroll view and pin a separate action bar to the bottom edge of the window. Keep capture results in the main content area so the bottom bar stays compact.

**Tech Stack:** SwiftUI, XCTest, Xcode build/install flow

---

### Task 1: Add regression coverage for the fixed action bar layout

**Files:**
- Modify: `macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift`
- Inspect: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`

**Step 1: Write the failing test**

Add a test that reads `CaptureWindowView.swift` and asserts the view contains:
- a `ScrollView`
- a bottom-pinned action bar pattern such as `safeAreaInset(edge: .bottom)`

**Step 2: Run test to verify it fails**

Run: `cd macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/SmokeTests`

Expected: FAIL because the current view is a single vertical stack with no fixed bottom action bar.

**Step 3: Commit**

No commit yet; continue directly to implementation after the red test.

### Task 2: Implement the pinned bottom action bar

**Files:**
- Modify: `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`

**Step 1: Write minimal implementation**

- Wrap the main content sections in a `ScrollView`
- Move the status text and capture button into a bottom action bar using `safeAreaInset(edge: .bottom)`
- Keep the result card inside the scrollable content
- Reduce the note editor minimum height slightly so the first viewport is more useful

**Step 2: Run test to verify it passes**

Run: `cd macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS' -only-testing:NanobotCaptureTests/SmokeTests`

Expected: PASS

**Step 3: Run the full macOS test suite**

Run: `cd macos/NanobotCapture && xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'`

Expected: PASS

### Task 3: Rebuild, reinstall, and verify the app on this Mac

**Files:**
- Rebuild app bundle from `macos/NanobotCapture`
- Replace: `~/Applications/NanobotCapture.app`

**Step 1: Build**

Run: `cd macos/NanobotCapture && xcodebuild build -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -configuration Debug -destination 'platform=macOS'`

Expected: `BUILD SUCCEEDED`

**Step 2: Reinstall**

Run: `ditto ~/Library/Developer/Xcode/DerivedData/.../Build/Products/Debug/NanobotCapture.app ~/Applications/NanobotCapture.app`

Expected: installed app replaced successfully

**Step 3: Relaunch and verify**

- Quit and reopen `~/Applications/NanobotCapture.app`
- Confirm the bottom capture button is visible immediately on window open

**Step 4: Commit**

```bash
git add docs/plans/2026-03-14-capture-window-fixed-action-bar-design.md \
  docs/plans/2026-03-14-capture-window-fixed-action-bar-implementation.md \
  macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift \
  macos/NanobotCapture/NanobotCaptureTests/SmokeTests.swift
git commit -m "feat: pin capture window action bar"
```
