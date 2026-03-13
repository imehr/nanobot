# Hybrid Knowledge Capture Guide

This guide explains the capture system now available in `nanobot`, including the native macOS app, menu bar UI, and Share extension.

## What You Get

All capture methods feed the same hybrid knowledge pipeline:

- `inbox/` keeps the raw original first
- `entities/` stores canonical facts and histories
- `ledgers/` stores structured transactions
- `indexes/` supports retrieval

Available capture paths:

- CLI capture commands
- watched folders
- local browser inbox
- chat `/capture` flows
- native macOS app window
- native macOS menu bar capture
- native macOS Share extension

## One-Time Setup

### 1. Configure `~/.nanobot/config.json`

Add or merge this:

```json
{
  "knowledge": {
    "enabled": true,
    "watchedPaths": [
      "~/Inbox/nanobot"
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

- `localWeb` is for browser/LAN capture.
- `nativeCapture` is only for the macOS app and Share extension.
- Keep `nativeCapture.bind` on `127.0.0.1`.
- Use a real random token for `nativeCapture.authToken`.

### 2. Create the watched folder

```bash
mkdir -p ~/Inbox/nanobot
```

### 3. Start the gateway

```bash
nanobot gateway
```

If configured correctly, startup output will include:

- `Local web inbox: http://127.0.0.1:18791/capture`
- `Native capture endpoint: http://127.0.0.1:18792/capture`
- `Watched folders: ~/Inbox/nanobot`

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

## How To Use Each Mac Capture Flow

### Menu Bar Capture

After the app is running, look for the `Nanobot` icon in the menu bar.

Use it for quick capture:

- paste or type a note
- add an optional hint like `bike`
- pull in clipboard text
- submit immediately
- open the full window when you need drag-drop or a larger form

Good use cases:

- a copied phone number
- a quick fact like tire pressure
- a short note about a vendor or recurring service centre

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

### Native Share Extension

Once the app has been built and run, `Nanobot` should appear in the macOS Share menu for supported apps.

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

- try running the app once from Xcode again
- in a Share panel, choose `More...` and enable `Nanobot` if macOS shows the extension as disabled

## Other Capture Methods

### CLI

```bash
nanobot capture text "Front tire pressure is 35 psi and rear is 38 psi" --hint bike
nanobot capture clipboard --hint bike
nanobot capture file ~/Downloads/service-invoice.pdf --hint bike --note "10,000 km service"
```

### Watched Folder

Drop files into:

- `~/Inbox/nanobot`

The gateway watcher picks them up and routes them automatically.

### Browser Inbox

Open:

- [http://127.0.0.1:18791/](http://127.0.0.1:18791/)

Use this when:

- you want a local web form
- you are on another machine on your LAN
- you want to upload files without opening the macOS app

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

Browser/LAN inbox:

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

- the app bundle was built and run successfully
- the share panel `More...` section has the extension enabled

### The browser inbox works but the app does not

That usually means:

- `localWeb` is enabled
- `nativeCapture` is not enabled or its token does not match

Remember: these are two separate endpoints by design.
