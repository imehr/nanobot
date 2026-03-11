# macOS Native Capture Design

**Date:** 2026-03-11

## Goal

Add a local-only macOS-native capture layer for nanobot so the user can send text, files, screenshots, URLs, and app shares into the hybrid knowledge system through:

- a menu bar app
- a normal app window
- a native macOS Share extension

The native layer must be secure by default and must not expose the internal knowledge base for arbitrary reading.

## Problem

The current capture paths are functional but not fully native on macOS:

- CLI capture commands
- watched folder
- browser inbox
- Telegram `/capture`

These cover capture, but they do not provide the expected macOS-native interaction model:

- top menu bar access
- app icon and window
- Share menu integration from Finder, Safari, Preview, and other apps

The user wants local-only macOS-native UX, not App Store distribution.

## Constraints

- The solution is only for this Mac.
- App Store distribution is not required.
- Apple Developer signing is not required for the first pass.
- The Share extension must be part of a real macOS app bundle.
- The native layer must be capture-only in the first version.
- Retrieval remains in nanobot itself; the app is not a knowledge browser.

## Recommended Approach

Build a native Swift/SwiftUI macOS app bundle with three targets:

1. `NanobotCapture` app target
2. `NanobotCaptureShareExtension` Share extension target
3. shared Swift code for payload assembly and submission

On the Python side, add a dedicated native capture endpoint that is separate from the current LAN/browser inbox.

## Architecture

### Python side

Add a new local-native capture service dedicated to the macOS app and Share extension.

Properties:

- bind to `127.0.0.1` only
- write-only capture endpoint
- no read/list/download APIs
- separate auth secret from the LAN/browser inbox
- preserve original file first, then hand off to the existing knowledge intake service

This service should reuse the current knowledge routing and storage pipeline so there is still only one source of routing truth.

### macOS side

Create a native macOS app project under `macos/`.

Components:

- SwiftUI app window for full capture
- menu bar extra for quick capture
- Share extension compose UI for app shares
- shared submission client for local-native endpoint calls
- Keychain-backed storage for local auth secret

The app and extension submit captures only. They do not browse the knowledge store directly.

## User Experience

### Menu bar app

Behavior:

- click menu bar icon to open a compact capture panel
- paste text
- attach files
- capture clipboard
- add optional note and hint
- submit directly into nanobot
- show last result and any follow-up question

### Full app window

Behavior:

- normal macOS app icon and app window
- drag-drop files
- paste text
- add optional note and hint
- submit multi-file and mixed-content captures
- show result summary after submission

### Share extension

Behavior:

- appears in the macOS Share menu
- available from host apps that expose standard share targets
- receives files, text, URLs, or images from the host app
- shows a small compose sheet with optional note and hint
- submits the shared content into nanobot

## Security Model

The design must avoid turning the app into a general-purpose front door to the knowledge base.

Rules:

- native endpoint is local-only
- native endpoint is capture-only
- no entity listing
- no artifact listing
- no file reads
- no search or retrieval API in v1
- Share extension can only submit what the user explicitly shared
- app and extension use a separate local secret
- secret is stored in macOS Keychain on the client side
- server logs do not contain secrets

Security boundary:

- app -> local-native capture endpoint -> existing knowledge pipeline
- app does not directly access entity/artifact storage

This keeps the sensitive data plane inside nanobot while allowing ergonomic local capture.

## Why Not Reuse The LAN Inbox Directly

Reusing the current browser inbox for the Mac app is possible, but not ideal:

- it is designed for browser and LAN use
- it does not enforce the tighter local-only security boundary
- it mixes native and cross-device trust assumptions

A dedicated native endpoint is a cleaner boundary.

## Why Not Build A Knowledge Browser

That is out of scope for v1 because it creates a larger attack surface and more product complexity.

The first version should stay focused on capture:

- menu bar quick intake
- full window intake
- Share extension intake

## Rollout

Recommended rollout order:

1. native local endpoint in Python
2. Swift app shell and submission client
3. full app window
4. menu bar quick capture
5. Share extension
6. docs and install notes

## Testing Strategy

### Python

- auth rejection tests
- loopback-only binding tests
- capture-only route tests
- file preservation tests
- knowledge service integration tests

### Swift

- app-side payload construction tests
- submission client tests
- manual end-to-end validation for Share extension payload types

### Manual end-to-end

- paste text through menu bar
- drag-drop PDF into app window
- share a file from Finder
- share a page from Safari
- share a PDF from Preview
- confirm capture lands in inbox and routes through knowledge storage

## Success Criteria

The feature is successful when:

- the user can capture from the menu bar without opening a browser
- the user can open a normal macOS app window and submit mixed captures
- `Nanobot` appears in the macOS Share menu for supported apps
- captures flow into the existing knowledge pipeline
- no new read access to the internal knowledge base is exposed
- the native endpoint is local-only and secured separately from the LAN inbox

## Decision

Proceed with a native Swift/SwiftUI macOS app bundle plus a dedicated local-native Python capture endpoint.
