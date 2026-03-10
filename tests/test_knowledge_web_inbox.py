import json
from pathlib import Path

from nanobot.knowledge.web_inbox import build_capture_response, build_inbox_page


def test_build_capture_response_includes_follow_up() -> None:
    payload = build_capture_response(
        inbox_item_path=Path("/tmp/item"),
        entities=["personal/bike"],
        actions=["saved original", "updated bike history"],
        follow_up="Is this personal or business?",
    )

    body = json.loads(payload)

    assert body["entities"] == ["personal/bike"]
    assert body["follow_up"] == "Is this personal or business?"


def test_build_inbox_page_includes_upload_form() -> None:
    page = build_inbox_page()

    assert 'method="post"' in page.lower()
    assert 'enctype="multipart/form-data"' in page
    assert 'type="file"' in page.lower()
