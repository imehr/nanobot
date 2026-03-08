# Agent Browser Browser Automation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a native `agent_browser` tool to `nanobot` for browser automation, keep non-browser MCP support unchanged, and preserve the existing `smaug` X bookmarks workflow.

**Architecture:** Introduce a first-class browser tool and browser config in `nanobot`, backed by the `agent-browser` CLI instead of MCP. Register the tool in the main agent loop, derive stable per-conversation browser sessions, and keep `smaug` bookmark fetching on `bird` with only documentation and compatibility verification changes.

**Tech Stack:** Python 3.11, Typer, Pydantic, asyncio subprocess execution, pytest, existing nanobot tool registry, `agent-browser` CLI

---

### Task 1: Add browser tool config schema

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/config/schema.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_agent_browser_tool.py`

**Step 1: Write the failing test**

Add a config-focused test covering default browser settings:

```python
from nanobot.config.schema import Config


def test_browser_tool_config_defaults() -> None:
    config = Config.model_validate({})
    assert config.tools.browser.enabled is True
    assert config.tools.browser.command == "agent-browser"
    assert config.tools.browser.headless is True
    assert config.tools.browser.timeout == 60
    assert config.tools.browser.extra_args == []
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_agent_browser_tool.py::test_browser_tool_config_defaults -v
```

Expected: FAIL because `ToolsConfig` does not yet expose `browser`.

**Step 3: Write minimal implementation**

Add new config models near `ExecToolConfig` and `ToolsConfig`:

```python
class BrowserToolConfig(Base):
    enabled: bool = True
    command: str = "agent-browser"
    headless: bool = True
    timeout: int = 60
    cdp_url: str = ""
    extra_args: list[str] = Field(default_factory=list)


class ToolsConfig(Base):
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    browser: BrowserToolConfig = Field(default_factory=BrowserToolConfig)
    restrict_to_workspace: bool = False
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_agent_browser_tool.py::test_browser_tool_config_defaults -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/config/schema.py tests/test_agent_browser_tool.py
git commit -m "feat: add browser tool config"
```

### Task 2: Add a session-aware `agent_browser` tool

**Files:**
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/agent/tools/agent_browser.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_agent_browser_tool.py`

**Step 1: Write the failing tests**

Add tests for the new tool’s public behavior:

```python
import pytest

from nanobot.agent.tools.agent_browser import AgentBrowserTool


def test_agent_browser_tool_name() -> None:
    tool = AgentBrowserTool()
    assert tool.name == "agent_browser"


@pytest.mark.asyncio
async def test_agent_browser_requires_action() -> None:
    tool = AgentBrowserTool()
    result = await tool.execute(action="unknown")
    assert "unsupported action" in result.lower()
```

Add subprocess and session tests:

```python
@pytest.mark.asyncio
async def test_agent_browser_builds_stable_session_key(monkeypatch) -> None:
    tool = AgentBrowserTool()
    tool.set_context(channel="telegram", chat_id="123", session_key="abc")
    assert tool._session_name() == "nanobot-telegram-123-abc"
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_agent_browser_tool.py -v
```

Expected: FAIL because the tool module does not exist.

**Step 3: Write minimal implementation**

Create the tool with:

- a `Tool` subclass named `AgentBrowserTool`
- a small action schema:
  - `open`
  - `snapshot`
  - `click`
  - `fill`
  - `extract`
  - `screenshot`
  - `close`
- a `set_context(channel, chat_id, session_key)` method
- stable session naming derived from context
- CLI argument building via `asyncio.create_subprocess_exec`
- timeout handling
- JSON stdout parsing when available
- explicit user-facing errors for missing binary and malformed output

Core outline:

```python
class AgentBrowserTool(Tool):
    def __init__(self, command: str = "agent-browser", headless: bool = True, timeout: int = 60, cdp_url: str = "", extra_args: list[str] | None = None):
        ...

    def set_context(self, channel: str, chat_id: str, session_key: str | None = None) -> None:
        ...

    def _session_name(self) -> str:
        ...

    async def execute(self, action: str, url: str = "", target: str = "", value: str = "", query: str = "", path: str = "", session: str = "", **kwargs: Any) -> str:
        ...
```

**Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_agent_browser_tool.py -v
```

Expected: PASS for basic schema, session naming, and unsupported-action checks.

**Step 5: Commit**

```bash
git add nanobot/agent/tools/agent_browser.py tests/test_agent_browser_tool.py
git commit -m "feat: add native agent-browser tool"
```

### Task 3: Cover CLI invocation, parsing, and failures with tests

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_agent_browser_tool.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/agent/tools/agent_browser.py`

**Step 1: Write the failing tests**

Add focused async tests that monkeypatch subprocess creation:

```python
@pytest.mark.asyncio
async def test_open_action_passes_url_to_cli(monkeypatch) -> None:
    ...
    assert captured_cmd[:2] == ["agent-browser", "open"]
    assert "https://example.com" in captured_cmd


@pytest.mark.asyncio
async def test_missing_binary_returns_actionable_error(monkeypatch) -> None:
    ...
    assert "install agent-browser" in result.lower()


@pytest.mark.asyncio
async def test_invalid_json_falls_back_to_raw_output(monkeypatch) -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_agent_browser_tool.py -v
```

Expected: FAIL on subprocess behavior not yet implemented.

**Step 3: Write minimal implementation**

Implement:

- `_build_command(...)` for each action
- `_run_command(...)` to execute subprocesses
- `FileNotFoundError` handling
- timeout handling
- stdout parsing:
  - prefer JSON result normalization
  - fall back to raw text when JSON is absent

Normalization should preserve element references in tool output if `agent-browser` returns them.

**Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_agent_browser_tool.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/tools/agent_browser.py tests/test_agent_browser_tool.py
git commit -m "test: cover agent-browser command handling"
```

### Task 4: Register browser context in the agent loop

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/agent/loop.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_agent_browser_tool.py`

**Step 1: Write the failing tests**

Add tests that verify:

- the tool is registered when browser config is enabled
- session context is updated before tool execution

Example test shape:

```python
def test_agent_loop_registers_browser_tool(...) -> None:
    loop = AgentLoop(..., browser_config=BrowserToolConfig(enabled=True))
    assert loop.tools.has("agent_browser")
```

```python
def test_set_tool_context_updates_browser_tool(...) -> None:
    ...
    loop._set_tool_context("telegram", "123", "abc")
    assert browser_tool._session_name() == "nanobot-telegram-123-abc"
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_agent_browser_tool.py -v
```

Expected: FAIL because `AgentLoop` does not yet accept browser config or propagate context.

**Step 3: Write minimal implementation**

Modify `AgentLoop` to:

- accept `browser_config` in `__init__`
- register `AgentBrowserTool` in `_register_default_tools()` when enabled
- update browser tool context in `_set_tool_context(...)`

Suggested change shape:

```python
self.browser_config = browser_config or BrowserToolConfig()
...
if self.browser_config.enabled:
    self.tools.register(AgentBrowserTool(...))
...
if browser_tool := self.tools.get("agent_browser"):
    if isinstance(browser_tool, AgentBrowserTool):
        browser_tool.set_context(channel, chat_id, message_id)
```

Use `session_key` rather than `message_id` if that better matches the actual conversation identity available at call time.

**Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_agent_browser_tool.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/loop.py tests/test_agent_browser_tool.py
git commit -m "feat: register browser tool in agent loop"
```

### Task 5: Wire browser config through CLI entrypoints

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/cli/commands.py`
- Test: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_commands.py`

**Step 1: Write the failing test**

Add or extend a command construction test that verifies `AgentLoop` receives browser config:

```python
def test_agent_command_passes_browser_config(monkeypatch) -> None:
    captured = {}
    ...
    assert captured["browser_config"].enabled is True
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_commands.py -k browser -v
```

Expected: FAIL because CLI commands do not pass browser config yet.

**Step 3: Write minimal implementation**

Update all `AgentLoop(...)` call sites in `nanobot/cli/commands.py` to pass:

```python
browser_config=config.tools.browser,
```

Relevant call sites include gateway, direct CLI agent mode, and any auxiliary direct-chat agent instances.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_commands.py -k browser -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/cli/commands.py tests/test_commands.py
git commit -m "feat: wire browser config through commands"
```

### Task 6: Update documentation for browser automation and Smaug compatibility

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/README.md`
- Modify: `/Users/mehranmozaffari/Documents/github/smaug/README.md`
- Modify: `/Users/mehranmozaffari/Documents/github/smaug/SETUP.md`

**Step 1: Write the failing docs check**

Use targeted searches as the initial failing check:

```bash
rg -n "MCP.*browser|browser automation" README.md
rg -n "bird CLI|Twitter session cookies|extract-cookies" /Users/mehranmozaffari/Documents/github/smaug/README.md /Users/mehranmozaffari/Documents/github/smaug/SETUP.md
```

Expected: current docs do not explain the new `agent-browser` path or the fact that Smaug fetch stays on `bird`.

**Step 2: Update documentation**

In `nanobot/README.md`:

- keep MCP section for non-browser tools
- add a browser automation section stating:
  - use `agent-browser`
  - browser automation is native, not MCP-based
  - install/config basics

In `smaug/README.md` and `smaug/SETUP.md`:

- clarify that bookmark fetching still uses `bird`
- clarify that any future browser automation via `nanobot` should use `agent-browser`, not MCP

**Step 3: Run the docs check**

Run:

```bash
rg -n "agent-browser|bird CLI|MCP" /Users/mehranmozaffari/Documents/github/nanobot/README.md /Users/mehranmozaffari/Documents/github/smaug/README.md /Users/mehranmozaffari/Documents/github/smaug/SETUP.md
```

Expected: output shows the new documented browser path and the preserved Smaug ingestion path.

**Step 4: Commit**

```bash
git add README.md /Users/mehranmozaffari/Documents/github/smaug/README.md /Users/mehranmozaffari/Documents/github/smaug/SETUP.md
git commit -m "docs: document agent-browser integration"
```

### Task 7: Verify non-browser MCP and browser tool behavior

**Files:**
- Modify if needed: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_commands.py`
- Modify if needed: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_agent_browser_tool.py`

**Step 1: Add the failing regression tests**

Add tests that confirm:

- MCP config still parses
- `AgentLoop` still accepts `mcp_servers`
- browser tool registration does not remove or rename MCP tools

Example:

```python
def test_tools_config_keeps_mcp_servers() -> None:
    config = Config.model_validate({"tools": {"mcpServers": {"fs": {"command": "npx"}}}})
    assert "fs" in config.tools.mcp_servers
```

**Step 2: Run tests to verify they fail only if regressions exist**

Run:

```bash
pytest tests/test_agent_browser_tool.py tests/test_commands.py tests/test_tool_validation.py -v
```

Expected: PASS once implementation is stable.

**Step 3: Adjust implementation only if needed**

If any regression appears:

- restore backward-compatible config aliases,
- keep MCP connection lifecycle unchanged,
- keep browser registration additive only.

**Step 4: Commit**

```bash
git add tests/test_agent_browser_tool.py tests/test_commands.py nanobot/config/schema.py nanobot/agent/loop.py
git commit -m "test: protect mcp compatibility with browser tool"
```

### Task 8: Run final verification and capture manual Smaug checks

**Files:**
- No required file changes unless a verification note is added to docs

**Step 1: Run focused automated tests**

Run:

```bash
pytest tests/test_agent_browser_tool.py tests/test_commands.py tests/test_tool_validation.py -v
```

Expected: PASS

**Step 2: Run broader command smoke**

Run:

```bash
pytest tests/test_commands.py -v
```

Expected: PASS

**Step 3: Manual Smaug compatibility smoke**

From `/Users/mehranmozaffari/Documents/github/smaug`, run:

```bash
node extract-cookies.js --json
```

Expected:

- either successful cookie extraction from a signed-in Chrome profile, or
- a clear auth-related error proving the existing non-MCP path is still the one in use.

Then run:

```bash
npx smaug --help
```

Expected: CLI still starts normally and shows bookmark commands.

**Step 4: Manual browser-tool smoke**

From `/Users/mehranmozaffari/Documents/github/nanobot`, run a tiny direct exercise once wired:

```bash
python - <<'PY'
from nanobot.agent.tools.agent_browser import AgentBrowserTool
import asyncio

async def main():
    tool = AgentBrowserTool()
    tool.set_context("cli", "direct", "smoke")
    print(await tool.execute(action="open", url="https://example.com"))

asyncio.run(main())
PY
```

Expected: either a successful open/snapshot style response, or a clear actionable install/config error if `agent-browser` is absent.

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: add native agent-browser automation"
```
