import json
from pathlib import Path

from nanobot.knowledge.web_inbox import build_capture_response, build_inbox_page, build_result_page


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
    assert "multiple" in page.lower()


def test_build_result_page_shows_entities_and_actions() -> None:
    page = build_result_page(
        entities=["personal/bike"],
        actions=["saved original", "applied decision"],
        follow_up=None,
    )

    assert "personal/bike" in page
    assert "saved original" in page
