# Persistent Capture Shell And Share Polish Design

## Problem

The current redesign fixed the screenshot attachment path, but two UX problems remain:

1. The capture window still behaves like one large scrolling surface. When attachments grow, the footer can disappear from view and the app no longer feels like a stable capture tool.
2. The Share extension is installed, but it still does not surface reliably in Notes, and when it does launch it should provide a clearer confirmation flow instead of immediately disappearing after submit.

There is also a window lifecycle issue:

- opening capture repeatedly can leave multiple capture windows around instead of reusing a single app window

## Goals

- Make the app window a persistent shell with:
  - fixed header
  - independently scrolling body
  - fixed footer/action bar
- Reuse one capture window instead of opening duplicates
- Broaden Share activation so Notes and similar apps can surface Nanobot
- Show a clear share confirmation state after successful submission

## Approaches

### 1. Patch the current window and keep `WindowGroup`

This is the minimum effort approach, but it preserves the multi-window behavior and the current shell ambiguity.

### 2. Move to a true single-window app shell and broaden share activation

Use a single `Window` scene, split the shell into fixed header/body/footer regions, and simplify Share activation so macOS can surface Nanobot from more hosts. This is the recommended path.

### 3. Add a separate custom importer for Notes and keep Share narrow

This is more work and unnecessary if the standard Share extension can be made broad enough for local use.

## Recommendation

Use approach 2.

This is the smallest change that solves the actual user-facing issues:
- no more stale duplicate capture windows
- header/footer remain visible
- Share becomes more broadly available
- successful share has an explicit completion state

## Design

### App Shell

The app window should be restructured as:

1. Fixed header
2. Scrollable middle region
3. Fixed footer/action bar

Only the middle region should scroll.

The attachment panel can scroll internally if it grows, but the footer and main action must remain pinned and visible.

### Single Window Behavior

The capture app should expose exactly one main capture window.

Opening from:
- menu bar
- clipboard action
- app icon

should always focus or reuse the existing capture window instead of creating new ones.

The right scene type for this is a single `Window` instead of a `WindowGroup`.

### Share Activation

The current extension advertises only a narrow set of activation types.

For a local-only utility app, the simplest and most reliable option is to broaden the activation rule aggressively so Nanobot can appear in more Share contexts, including Notes. For this pass, correctness and usability matter more than strict selectivity.

### Share UI

When Nanobot is selected from a Share sheet:

- show what was prepared
- allow optional note/hint
- show a clear `Send to Nanobot` action

After success:
- show a success state in the Share view
- include the saved inbox path or a short confirmation summary
- let the user explicitly close/done, rather than dismissing instantly with no confirmation

## Success Criteria

- The app header is always visible.
- The app footer/action bar is always visible.
- Only one main capture window is used.
- Nanobot appears in Notes Share flows.
- After share submit, the user sees an explicit success confirmation before the extension closes.
