from pathlib import Path


def test_macos_capture_app_icon_assets_exist() -> None:
    appicon_dir = Path(
        "/Users/mehranmozaffari/Documents/github/nanobot/macos/NanobotCapture/"
        "NanobotCapture/Resources/Assets.xcassets/AppIcon.appiconset"
    )

    assert appicon_dir.exists()
    assert (appicon_dir / "Contents.json").exists()
    assert any(path.suffix == ".png" for path in appicon_dir.iterdir())
