# Responsive Capture Composer Design

## Problem

The current macOS `NanobotCapture` window has two user-visible failures:

1. The layout is brittle. Header content has been clipped by the titlebar area, the form feels squeezed, and the window behaves like a tall static form instead of adapting to available space.
2. Screenshot paste is unreliable in the real app. A screenshot copied to the clipboard should become an attachment in the window, but in practice the UI often shows `0 selected`, which means the capture action has nothing to submit.

The current behavior is not acceptable for the app's primary workflow. This pass should treat the issue as a redesign, not another incremental spacing patch.

## Goals

- Make the full capture window responsive and stable across normal Mac window sizes.
- Make screenshot paste work as a first-class workflow.
- Show pasted screenshots as attachments inside the window, not in a separate preview/modal flow.
- Keep the primary capture action visible at all times.
- Give immediate UI feedback when pasted content is attached or when capture fails.

## Non-Goals

- No knowledge browsing UI in the Mac app.
- No retrieval/search UX in this pass.
- No redesign of the backend routing pipeline beyond what is needed to support the frontend capture flow.

## Approaches

### 1. Keep the current single-column form and patch the paste flow

This is the lowest-effort option, but it keeps the same layout structure that already failed multiple times. It does not address the deeper usability problem.

### 2. Build a responsive capture composer

Use a real composer layout with a persistent header, a flexible main body, an attachment panel, and a fixed action bar. On wider windows, show content and attachments side-by-side. On narrower windows, stack them vertically. This solves both the UX and the screenshot workflow cleanly.

### 3. Split into separate screenshot and document modes

This would allow custom flows per content type, but it adds mode-switching complexity before the basic capture experience is reliable.

## Recommendation

Use approach 2: a responsive capture composer.

This keeps the architecture simple, preserves the current backend, and gives the app a window that behaves like a native capture tool instead of a repurposed web form.

## UX Design

### Window Structure

The window should have three persistent regions:

1. Header
   - Title: `Nanobot Capture`
   - Short supporting copy
   - Always visible and never clipped by the titlebar

2. Main body
   - Responsive layout
   - Wide windows: `Context` editor on the left, `Attachments` panel on the right
   - Narrow windows: sections stack vertically

3. Bottom action bar
   - Status message on the left
   - Primary action on the right
   - Always visible

### Attachments Panel

The existing large empty drop zone should become an actual attachments panel.

Behavior:
- Empty state shows drag-drop guidance plus `Choose Files` and `Paste Clipboard`
- Non-empty state shows attachment cards
- Images/screenshots show thumbnails
- Files like PDFs show filename-based cards
- Each card has a remove action
- A small count is visible

### Screenshot Paste

Desired behavior:
- `Command-V` or `Paste Clipboard` with an image on the clipboard adds an attachment card
- The attachment count updates immediately
- The status line confirms success, for example `Screenshot added`
- No separate preview window or modal should appear
- The screenshot should remain an attachment until the user removes it or submits

### Capture Button State

The primary button should only enable when:
- the note contains non-whitespace text, or
- at least one attachment exists

If submission fails:
- keep the attachments in place
- show a direct error status
- do not silently clear state

## Technical Design

### Layout

Replace the current `ScrollView`-driven single-column layout with a responsive container that reacts to available width.

Suggested structure:
- `GeometryReader` or width-aware wrapper at the top level
- one layout branch for wide windows
- one layout branch for compact windows

The header should live outside the scrollable form body so it never drifts under the titlebar. Only the body should scroll if content exceeds the available height.

### Attachment Model

The current `selectedFiles: [URL]` model is enough for transport but not for good UI. The redesigned window should introduce a richer view model layer for attachments so the UI can render thumbnails and expose remove actions.

A practical shape is:
- stable `id`
- source `URL`
- `kind` such as image or generic file
- display name
- optional thumbnail

The capture submission path can still convert these back to file URLs for the native endpoint.

### Clipboard Handling

Clipboard paste should be normalized through one path:
- detect clipboard image/text/file content
- if image: write a temporary image file, create an attachment entry, generate a thumbnail
- if text: populate or append to context text
- if file URLs: add them as attachments

The important rule is that image clipboard content must always land in the attachment model, regardless of whether keyboard focus is currently inside the note editor.

### Error Handling

The app should distinguish between:
- `Clipboard had no supported content`
- `Screenshot added`
- `Capture failed: <reason>`
- `Capture saved`

The current ambiguous `Ready`/`0 selected` state is not enough.

## Testing

The redesign should be shipped only with:
- view-model tests for screenshot paste producing an attachment
- tests for enable/disable rules on the capture button
- tests for attachment removal
- a layout invariant test that the responsive mode switches as expected
- end-to-end manual verification on the installed app:
  - paste screenshot
  - see attachment thumbnail
  - submit successfully
  - verify saved inbox record

## Files Expected To Change

- `macos/NanobotCapture/NanobotCapture/UI/CaptureWindowView.swift`
- `macos/NanobotCapture/NanobotCapture/App/AppState.swift`
- `macos/NanobotCapture/NanobotCapture/UI/FileDropZone.swift`
- `macos/NanobotCapture/NanobotCapture/Client/...` only if request handling needs small adjustments
- `macos/NanobotCapture/NanobotCaptureTests/...`
- `docs/hybrid-knowledge-capture.md`
- `macos/NanobotCapture/README.md`

## Success Criteria

- The title/header is always fully visible.
- The window looks intentional at normal desktop sizes.
- Screenshot paste reliably adds an attachment card with a thumbnail.
- Clicking `Capture to Nanobot` succeeds when a pasted screenshot is present.
- The installed app on this Mac demonstrates the full flow end-to-end.
