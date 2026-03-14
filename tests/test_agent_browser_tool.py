import asyncio
import json
from pathlib import Path

import pytest

from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider, LLMResponse
from nanobot.config.schema import Config


def test_browser_tool_config_defaults() -> None:
    config = Config.model_validate({})
    assert config.tools.browser.enabled is True
    assert config.tools.browser.command == "agent-browser"
    assert config.tools.browser.headless is True
    assert config.tools.browser.timeout == 60
    assert config.tools.browser.extra_args == []
    assert config.tools.browser.session_prefix == "nanobot"


def test_mcp_servers_config_remains_available() -> None:
    config = Config.model_validate(
        {
            "tools": {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    }
                }
            }
        }
    )

    assert "filesystem" in config.tools.mcp_servers
    assert config.tools.mcp_servers["filesystem"].command == "npx"


def test_agent_browser_tool_name() -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    tool = AgentBrowserTool()
    assert tool.name == "agent_browser"


def test_agent_browser_tool_schema_exposes_core_actions() -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    tool = AgentBrowserTool()
    actions = tool.parameters["properties"]["action"]["enum"]
    assert actions == ["open", "snapshot", "click", "fill", "extract", "screenshot", "close"]


def test_agent_browser_builds_stable_session_name() -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    tool = AgentBrowserTool(session_prefix="nanobot")
    tool.set_context(channel="telegram", chat_id="12345", session_key="bookmark:run")
    assert tool._session_name() == "nanobot-telegram-12345-bookmark-run"


@pytest.mark.asyncio
async def test_agent_browser_rejects_unsupported_action() -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    tool = AgentBrowserTool()
    result = await tool.execute(action="hover")
    assert "unsupported action" in result.lower()


@pytest.mark.asyncio
async def test_agent_browser_open_builds_expected_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    captured: list[str] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return (
                json.dumps({"success": True, "data": {"url": "https://example.com"}}).encode(),
                b"",
            )

    async def fake_exec(*args, **kwargs):
        captured.extend(args)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    tool = AgentBrowserTool(command="agent-browser", headless=True, timeout=10)
    tool.set_context(channel="cli", chat_id="direct", session_key="smoke")

    result = await tool.execute(action="open", url="https://example.com")

    assert captured[:5] == [
        "agent-browser",
        "--session",
        "nanobot-cli-direct-smoke",
        "--session-name",
        "nanobot-cli-direct-smoke",
    ]
    assert "--json" in captured
    assert "open" in captured
    assert "https://example.com" in captured
    assert "https://example.com" in result


@pytest.mark.asyncio
async def test_agent_browser_snapshot_uses_interactive_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    captured: list[str] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            payload = {
                "success": True,
                "data": {
                    "snapshot": 'button "Submit" [ref=@e1]',
                    "refs": {"e1": {"role": "button", "name": "Submit"}},
                },
            }
            return (json.dumps(payload).encode(), b"")

    async def fake_exec(*args, **kwargs):
        captured.extend(args)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    tool = AgentBrowserTool()
    result = await tool.execute(action="snapshot")

    assert captured[-2:] == ["snapshot", "-i"]
    assert "--json" in captured
    assert "--headed" not in captured
    assert "@e1" in result
    assert "Submit" in result


@pytest.mark.asyncio
async def test_agent_browser_missing_binary_returns_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    async def fake_exec(*args, **kwargs):
        raise FileNotFoundError("agent-browser")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    tool = AgentBrowserTool()
    result = await tool.execute(action="snapshot")

    assert "install agent-browser" in result.lower()


@pytest.mark.asyncio
async def test_agent_browser_invalid_json_falls_back_to_raw_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nanobot.agent.tools.agent_browser import AgentBrowserTool

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return (b"plain output", b"")

    async def fake_exec(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    tool = AgentBrowserTool()
    result = await tool.execute(action="extract", target="@e1")

    assert result == "plain output"


class DummyProvider(LLMProvider):
    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.7):
        return LLMResponse(content="ok")

    def get_default_model(self) -> str:
        return "dummy/model"


def test_agent_loop_registers_browser_tool() -> None:
    from nanobot.agent.loop import AgentLoop
    from nanobot.config.schema import BrowserToolConfig

    loop = AgentLoop(
        bus=MessageBus(),
        provider=DummyProvider(),
        workspace=Path.cwd(),
        browser_config=BrowserToolConfig(enabled=True),
    )

    assert loop.tools.has("agent_browser")


def test_set_tool_context_updates_browser_tool_session() -> None:
    from nanobot.agent.loop import AgentLoop
    from nanobot.config.schema import BrowserToolConfig

    loop = AgentLoop(
        bus=MessageBus(),
        provider=DummyProvider(),
        workspace=Path.cwd(),
        browser_config=BrowserToolConfig(enabled=True),
    )

    loop._set_tool_context("telegram", "123", "bookmark:run")

    browser_tool = loop.tools.get("agent_browser")
    assert browser_tool is not None
    assert browser_tool._session_name() == "nanobot-telegram-123-bookmark-run"
