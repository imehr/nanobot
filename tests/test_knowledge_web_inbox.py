import json
from pathlib import Path

from nanobot.knowledge.web_inbox import build_capture_response


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
