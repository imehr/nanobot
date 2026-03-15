# Hybrid Knowledge Capture Guide

This guide explains the capture system now available in `nanobot`, including the native macOS app, menu bar UI, and Share extension.

## What You Get

All capture methods feed the same hybrid knowledge pipeline:

- `~/.nanobot/workspace/queue/` and related folders keep runtime queue state only
- `Mehr/` stores canonical organized memory
- `Mehr/Projects/` stores concise project summaries and decisions
- `Nanobot Archive/` stores preserved originals when evidence should be kept

Available capture paths:

- CLI capture commands
- watched folders
- local browser inbox
- chat `/capture` flows
- native macOS app window
- native macOS menu bar capture
- native macOS Share extension

## Memory Model

Use these three layers deliberately:

- repo docs
  - detailed engineering truth, design docs, implementation plans, ADR-style notes
- `Mehr`
  - canonical memory for entities, histories, ledgers, and project summaries
- `Nanobot Archive`
  - preserved originals outside `Mehr` so other AI tools do not see duplicate raw material

Project memory lives under:

- `Mehr/Projects/<project>/index.md`
- `Mehr/Projects/<project>/decisions.md`
- `Mehr/Projects/<project>/timeline.md`
- `Mehr/Projects/<project>/features/*.md`

This is where Nanobot stores short summaries of meaningful project work, while the repo keeps the full detail.

## This Mac Is Already Configured

On this Mac, the setup has already been applied for the user account `mehranmozaffari`.

Installed local pieces:

- watched folder: `~/Drop to Nanobot`
- `Nanobot Capture` for Web: `http://127.0.0.1:18791/`
- native app endpoint: `http://127.0.0.1:18792/`
- native app bundle: `/Applications/NanobotCapture.app`
- Finder Quick Action: `~/Library/Services/Send to Nanobot.workflow`
- text Service: `~/Library/Services/Send Text to Nanobot.workflow`

Config already applied:

- `~/.nanobot/config.json` has `knowledge.enabled = true`
- `knowledge.watchedPaths` includes `~/Drop to Nanobot`
- `knowledge.nativeCapture.enabled = true`
- `knowledge.nativeCapture.bind = 127.0.0.1`
- `knowledge.nativeCapture.port = 18792`
- `knowledge.canonicalRoot = ~/Library/Mobile Documents/com~apple~CloudDocs/Mehr`
- `knowledge.archiveRoot = ~/Library/Mobile Documents/com~apple~CloudDocs/Nanobot Archive`

If you are using this exact Mac, skip to `How To Use Each Mac Capture Flow`.

## One-Time Setup On Another Mac

### 1. Configure `~/.nanobot/config.json`

Add or merge this:

```json
{
  "knowledge": {
    "enabled": true,
    "watchedPaths": [
      "~/Drop to Nanobot"
    ],
    "localWeb": {
      "enabled": true,
      "bind": "127.0.0.1",
      "port": 18791,
      "authToken": ""
    },
    "nativeCapture": {
      "enabled": true,
      "bind": "127.0.0.1",
      "port": 18792,
      "authToken": "choose-a-long-random-token"
    }
  }
}
```

Notes:

- `localWeb` is for the browser-based `Nanobot Capture` app and LAN capture.
- `nativeCapture` is only for the macOS app and Share extension.
- Keep `nativeCapture.bind` on `127.0.0.1`.
- Use a real random token for `nativeCapture.authToken`.

### 2. Create the watched folder

```bash
mkdir -p ~/Drop\\ to\\ Nanobot
```

### 3. Start the gateway

```bash
nanobot gateway
```

If configured correctly, startup output will include:

- `Nanobot Capture for Web: http://127.0.0.1:18791/`
- `Native capture endpoint: http://127.0.0.1:18792/capture`
- `Watched folders: ~/Drop to Nanobot`

## Native macOS App

The native macOS project lives in `macos/NanobotCapture`.

It gives you three native entry points:

- menu bar app
- full app window
- Share extension

### Build and Run

1. Generate the Xcode project:

```bash
cd macos/NanobotCapture
xcodegen generate
open NanobotCapture.xcodeproj
```

2. In Xcode, select the `NanobotCapture` scheme.

3. Open `Product -> Scheme -> Edit Scheme...` and add these environment variables under `Run`:

- `NANOBOT_NATIVE_CAPTURE_BASE_URL=http://127.0.0.1:18792`
- `NANOBOT_NATIVE_CAPTURE_TOKEN=<the same token from knowledge.nativeCapture.authToken>`

4. Run the app once from Xcode.

This installs the app bundle locally and gives the app access to the same native endpoint as the Share extension.

The app also shows queued and processed capture status, including when a capture updates project memory under `Mehr/Projects/...`.

## How To Use Each Mac Capture Flow

### Menu Bar Capture

After the app is running, look for the `Nanobot` icon in the menu bar.

Use it for quick capture:

- paste or type a note
- add an optional hint like `bike`
- pull in clipboard text
- paste a screenshot or image from the clipboard with `Command-V`
- submit immediately
- open the full window when you need drag-drop or a larger form

Good use cases:

- a copied phone number
- a quick fact like tire pressure
- a short note about a vendor or recurring service centre
- a screenshot you copied with the macOS screenshot shortcut

### Full App Window

The main app window is the richer version of the same capture form.

Use it when you want:

- drag-drop files
- attach multiple files
- combine note + hint + attachments
- see the routing result clearly after submit

Good use cases:

- invoices
- receipts
- PDFs
- screenshots
- a service booking confirmation plus a note explaining context

Clipboard screenshot flow:

1. Copy a screenshot to the clipboard with `Shift-Command-Control-4` for a region or `Shift-Command-Control-3` for the full screen.
2. Open `NanobotCapture.app`.
3. Press `Command-V` in the main window, or click `Paste Clipboard`.
4. Confirm the screenshot appears in the Attachments panel as a thumbnail card and the status changes to `Screenshot added`.
5. Click `Capture to Nanobot`.

If the processed capture updates project memory, the result state prefers that destination and the recent-captures list marks it as `Project Memory`.

### Native Share Extension

`Nanobot` is registered as a macOS Share service on this machine and should appear in the Share menu for supported apps.

Typical flow:

1. In Finder, Safari, Preview, Photos, or another app with Share support, choose `Share`.
2. Pick `Nanobot`.
3. Add an optional note and hint.
4. Submit.

The Share extension accepts:

- files
- URLs
- plain text
- images

If `Nanobot` does not appear at first:

- quit and reopen `NanobotCapture.app`
- in a Share panel, choose `More...` and enable `Nanobot` if macOS shows the extension as disabled

### Finder Quick Action

There is also a native Finder Quick Action installed on this Mac:

- `Send to Nanobot`

Use it like this:

1. Select one or more files in Finder.
2. Right-click.
3. Choose `Quick Actions`, then `Send to Nanobot`.

This is best for:

- screenshots
- PDFs
- invoices
- downloaded receipts
- images you want routed into knowledge without opening the browser or app window

This Quick Action uses the same local `nanobot capture file ...` path as the other native tools.

### Native Text Service

There is also a text Service installed on this Mac:

- `Send Text to Nanobot`

Use it like this:

1. Select text in a Mac app that exposes the Services menu.
2. Right-click or open the app menu.
3. Choose `Services`, then `Send Text to Nanobot`.

This is the lightest native path for:

- copied booking details
- addresses
- phone numbers
- instructions from email or chat
- snippets from a web page

### Clipboard Launcher App

There is a small local launcher app installed on this Mac:

- `~/Applications/Send Clipboard to Nanobot.app`

Use it like this:

1. Copy some text.
2. Launch `Send Clipboard to Nanobot` from Spotlight, Launchpad, or Finder.
3. The app sends the current clipboard text directly into Nanobot.

This is the simplest native clipboard path when you do not want to open Terminal or the full Nanobot window.

## Other Capture Methods

### CLI

```bash
nanobot capture text "Front tire pressure is 35 psi and rear is 38 psi" --hint bike
nanobot capture clipboard --hint bike
nanobot capture file ~/Downloads/service-invoice.pdf --hint bike --note "10,000 km service"
```

### Watched Folder

Drop files into:

- `~/Drop to Nanobot`

The gateway watcher picks them up and routes them automatically.

### Nanobot Capture for Web

Open:

- [http://127.0.0.1:18791/](http://127.0.0.1:18791/)

Use this when:

- you want the browser version of the `Nanobot Capture` composer
- you are on another machine on your LAN
- you want to upload files without opening the macOS app

Browser behavior now matches the desktop app more closely:

- responsive two-pane composer
- drag-drop attachments
- pasted clipboard screenshots/images
- queue-aware result states
- recent captures list

### Mobile / Chat

Use:

- `/capture ...` in Telegram or other supported chat channels

Example:

```text
/capture This invoice is for my bike and should be treated as personal
```

Attach a file when needed. `nanobot` preserves the original before routing it.

## What Happens After You Send Something

For every capture, `nanobot` does this:

1. saves the original first
2. classifies the material
3. identifies likely entities such as `personal/bike`
4. updates canonical files when the content contains durable facts
5. appends history when it represents an event
6. creates ledger entries when it is transactional
7. asks a follow-up only when ambiguity changes storage or treatment

Example:

- a bike service invoice can end up in `entities/personal/bike/artifacts/`
- the service event can be appended to `entities/personal/bike/history.md`
- the spend can be added to `ledgers/expenses.csv`

## Security Model

The native macOS layer is intentionally narrower than the browser inbox.

Native app and Share extension:

- submit only to `127.0.0.1:18792`
- use a separate bearer token
- have no read, list, or browse API
- cannot query your full knowledge base

Browser/LAN `Nanobot Capture`:

- uses the separate `localWeb` service on `127.0.0.1:18791`
- can be exposed to your LAN if you choose, but that is separate from the native app

Recommended defaults:

- keep `nativeCapture.bind` as `127.0.0.1`
- set a non-empty `nativeCapture.authToken`
- only expose `localWeb` to the LAN if you actually need browser access from other machines

## Troubleshooting

### The app submits nothing

Check:

- `nanobot gateway` is running
- `knowledge.nativeCapture.enabled` is `true`
- the scheme env vars in Xcode match your config token and port

### The Share extension opens but fails to send

Check:

- the app has been run at least once
- `NANOBOT_NATIVE_CAPTURE_TOKEN` matches `knowledge.nativeCapture.authToken`
- the native endpoint is healthy:

```bash
curl http://127.0.0.1:18792/health
```

### `Nanobot` does not appear in the Share menu

Check:

- the installed app at `~/Applications/NanobotCapture.app` is the latest build
- quit and reopen `NanobotCapture.app` once after reinstalling
- the share panel `More...` section has the extension enabled

If you want to confirm registration from Terminal:

```bash
pluginkit -m -p com.apple.share-services | rg nanobot
```

You should see `ai.nanobot.capture.share(1.0)`.

### The browser inbox works but the app does not

That usually means:

- `localWeb` is enabled
- `nativeCapture` is not enabled or its token does not match

Remember: these are two separate endpoints by design.
