# NanobotCapture

Local macOS app bundle for native nanobot capture.

Targets:

- `NanobotCapture` app
- `NanobotCaptureTests` unit tests
- `NanobotCaptureShareExtension` Share extension

## Requirements

- full Xcode
- `xcodegen`
- running `nanobot gateway` with `knowledge.nativeCapture.enabled = true`

## Project generation

```bash
cd macos/NanobotCapture
xcodegen generate
```

## Running locally

1. Generate the project:

```bash
cd macos/NanobotCapture
xcodegen generate
open NanobotCapture.xcodeproj
```

2. In Xcode, edit the `NanobotCapture` scheme and add these `Run` environment variables:

- `NANOBOT_NATIVE_CAPTURE_BASE_URL=http://127.0.0.1:18792`
- `NANOBOT_NATIVE_CAPTURE_TOKEN=<match knowledge.nativeCapture.authToken>`

3. Make sure the Python side is running:

```bash
nanobot gateway
```

4. Run the app from Xcode.

The app will:

- show a menu bar capture panel
- expose a full responsive app window for drag-drop and multi-file capture
- install the Share extension for supported macOS Share flows
- accept pasted images and screenshots in the main window via `Command-V` or `Paste Clipboard`
- show pasted screenshots as attachment cards with thumbnails before submission

## Verified local flows

- Share service registration: `pluginkit -m -p com.apple.share-services | rg nanobot`
- Screenshot to clipboard: `Shift-Command-Control-4`, then `Command-V` in the app window and confirm the screenshot appears in the attachment panel
- Native endpoint health: `curl http://127.0.0.1:18792/health`

## Tests

```bash
xcodegen generate
xcodebuild test -project "$(pwd)/NanobotCapture.xcodeproj" -scheme NanobotCapture -destination 'platform=macOS'
```

## Security boundary

The app and extension submit captures only.

They do not:

- browse entities
- list artifacts
- read the knowledge store

All payloads go through the separate loopback-only native capture endpoint on `127.0.0.1:18792`.
