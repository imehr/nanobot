# Web Nanobot Capture Alignment Design

## Summary

Align the local browser capture UI with the current macOS `Nanobot Capture` app so the web surface feels like the same product rather than an older side tool. The browser version should adopt the same naming, shared red capture icon, responsive two-pane layout, queue-aware result model, and attachment behavior wherever the browser platform allows it.

## Goals

- Rename the browser inbox from `nanobot inbox` to `Nanobot Capture`.
- Match the current macOS capture app visual structure: persistent header, responsive composer, persistent footer action bar.
- Introduce the shared capture branding: red document-memory icon across web, macOS app, and capture-facing metadata.
- Support the same core capture behaviors in browser:
  - note/context entry
  - hint entry
  - multi-file selection
  - drag-and-drop attachments
  - clipboard screenshot/image paste
  - visible queue/progress/result states
- Expose recent captures in the browser, using the same status vocabulary as the desktop app.

## Non-Goals

- Replacing the broader `Nanobot` brand with `Nanobot Capture`.
- Building a full browser-based file manager for `Mehr`, archives, or queue internals.
- Browser parity for macOS-only actions such as direct Finder reveal.
- Internet-facing deployment changes or auth redesign beyond the current local capture service.

## Product Model

- `Nanobot` remains the overall system.
- `Nanobot Capture` is the dedicated intake product.
- Capture surfaces should share one product identity:
  - macOS app
  - web capture UI
  - macOS share extension
  - capture-specific bot acknowledgements and labels where practical

This keeps capture distinct from the broader agent while giving users one recognizable intake surface everywhere.

## Branding

### Name

- Use `Nanobot Capture` as the visible name of the browser UI.
- Remove old `nanobot inbox` wording.
- Keep button and status language aligned with the desktop app:
  - `Capture to Nanobot`
  - `Queued`
  - `Processing`
  - `Completed`
  - `Failed`
  - `Retracted`

### Shared Icon

- Introduce a red-backed document-memory capture icon.
- Use it in:
  - macOS app icon metadata where practical
  - web page header
  - favicon / browser metadata
  - share extension branding if possible
  - capture acknowledgements in bot/channel surfaces where templates already exist

The icon should be simple and readable at favicon, menu, and app-icon sizes.

## Web UX

### Layout

Mirror the macOS app structure:

- Persistent header
  - icon
  - `Nanobot Capture` title
  - short capture-purpose description
- Responsive main composer
  - wide mode: context left, attachments/right-side activity on the right
  - compact mode: stacked sections
- Persistent footer action bar
  - queue/progress status
  - primary action button

### Composer

Left/primary column:
- `Context` multiline editor
- `Hint` field
- result card after submission

Right/secondary column:
- attachment drop zone
- `Choose Files`
- `Paste Clipboard`
- `Clear`
- attachment list/cards with thumbnails where applicable

Below the result card:
- `Recent Captures` list showing queue-aware state and destination info

### Behavior

Browser behavior should match the desktop app where possible:

- Drag-drop files into the attachment panel.
- Select multiple files from file picker.
- Paste text into context normally.
- Paste images/screenshots into attachments from clipboard.
- Show attachment cards immediately after paste/drop/select.
- Disable the main action while submitting.
- Show visible progress state while waiting for queue acknowledgement or status refresh.
- Render result state in the same language as the desktop app.

### Clipboard Support

Use a layered approach:

1. Listen for paste events and inspect clipboard items.
2. Prefer image blobs for screenshots and image clipboard content.
3. Fall back to text when image data is unavailable.
4. Keep the explicit `Paste Clipboard` button as a browser-permission fallback.

If the browser blocks clipboard access, show a clear in-UI error or hint rather than failing silently.

## Data And Queue Model

The web UI should not bypass the existing queue model.

Expected browser flow:

1. Submit capture to the current local web capture endpoint.
2. Receive queue-oriented response with `capture_id` and initial status.
3. Poll existing/added status endpoint for updates.
4. Show final canonical destination in `Mehr`.
5. Show archive location only when preserved.

The browser UI should stop presenting the raw inbox/staging location as the primary destination. The user-facing result should emphasize the organized destination in `Mehr`.

## Recent Captures

The web UI should expose recent captures similarly to the macOS app:

- capture id
- current status
- source channel
- primary destination
- project-memory badge when relevant
- retry/retract controls when supported by the backend

Browser-safe actions:
- open link if a URL is available
- copy destination path
- retry
- retract

Avoid Finder-specific affordances in the browser.

## Architecture

The existing `nanobot/knowledge/web_inbox.py` should evolve into a richer browser app generated by the local Python service, rather than creating a separate frontend stack.

Recommended approach:

- keep the local Python HTTP service
- replace the current minimal HTML/CSS page with a richer self-contained HTML/CSS/JS app
- add the minimum backend JSON/status support needed for parity with the queue model
- reuse existing queue and recent-captures data rather than inventing parallel state

This keeps the deployment model simple and consistent with the local-only architecture.

## Error Handling

The web UI should explicitly handle:

- clipboard permission failure
- empty submission attempts
- upload failure
- queue submission failure
- status polling failure
- retry/retract failure

For each case:
- show visible inline status
- preserve unsent user input where safe
- avoid full-page error dumps

## Testing

Coverage should include:

- HTML page contains `Nanobot Capture` branding
- page includes new structural sections for header/composer/footer
- page includes recent-captures UI hooks
- multipart upload behavior remains intact
- JSON/browser capture response stays compatible
- queue-aware result rendering includes canonical destination emphasis

If practical, add tests for:
- status endpoint payload shape used by the browser UI
- clipboard/paste script hooks appearing in the generated page markup

## Rollout

1. Update browser branding and layout structure.
2. Add queue/progress/recent-captures browser behavior.
3. Add shared icon assets and wire them into web metadata and capture-facing surfaces.
4. Verify browser capture, screenshot paste, and recent captures locally.
5. Merge to `main` and keep the repo clean.
