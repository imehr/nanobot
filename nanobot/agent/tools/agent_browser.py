"""Native browser automation tool backed by the agent-browser CLI."""

import asyncio
import json
import re
from typing import Any

from nanobot.agent.tools.base import Tool


class AgentBrowserTool(Tool):
    """Wrap the agent-browser CLI as a native nanobot tool."""

    _ACTIONS = ["open", "snapshot", "click", "fill", "extract", "screenshot", "close"]
    _GET_MODES = ["text", "html", "value", "attr", "title", "url", "count", "box", "styles"]

    def __init__(
        self,
        command: str = "agent-browser",
        headless: bool = True,
        timeout: int = 60,
        cdp_url: str = "",
        extra_args: list[str] | None = None,
        session_prefix: str = "nanobot",
    ):
        self.command = command
        self.headless = headless
        self.timeout = timeout
        self.cdp_url = cdp_url
        self.extra_args = extra_args or []
        self.session_prefix = session_prefix
        self._channel = "cli"
        self._chat_id = "direct"
        self._session_key = "direct"

    @property
    def name(self) -> str:
        return "agent_browser"

    @property
    def description(self) -> str:
        return "Control a browser using the agent-browser CLI for navigation, snapshots, clicks, form filling, extraction, and screenshots."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": self._ACTIONS,
                    "description": "Browser action to run.",
                },
                "url": {
                    "type": "string",
                    "description": "URL to open for the open action.",
                },
                "target": {
                    "type": "string",
                    "description": "Selector or ref such as @e1 for click, fill, and extract actions.",
                },
                "value": {
                    "type": "string",
                    "description": "Input value for the fill action.",
                },
                "mode": {
                    "type": "string",
                    "enum": self._GET_MODES,
                    "description": "Extraction mode for the extract action.",
                },
                "attribute": {
                    "type": "string",
                    "description": "Attribute name when extract mode is attr.",
                },
                "path": {
                    "type": "string",
                    "description": "Optional output path for the screenshot action.",
                },
            },
            "required": ["action"],
        }

    def set_context(self, channel: str, chat_id: str, session_key: str | None = None) -> None:
        """Set routing context so browser state can follow the conversation."""
        self._channel = channel or "cli"
        self._chat_id = chat_id or "direct"
        self._session_key = session_key or self._chat_id

    def _session_name(self) -> str:
        raw = f"{self.session_prefix}-{self._channel}-{self._chat_id}-{self._session_key}"
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-")
        return cleaned[:120] or self.session_prefix

    def _base_command(self) -> list[str]:
        cmd = [
            self.command,
            "--session",
            self._session_name(),
            "--session-name",
            self._session_name(),
            "--json",
        ]
        if self.cdp_url:
            cmd.extend(["--cdp", self.cdp_url])
        if not self.headless:
            cmd.append("--headed")
        if self.extra_args:
            cmd.extend(["--args", ",".join(self.extra_args)])
        return cmd

    def _build_command(
        self,
        action: str,
        url: str,
        target: str,
        value: str,
        mode: str,
        attribute: str,
        path: str,
    ) -> list[str] | None:
        cmd = self._base_command()
        if action == "open":
            if not url:
                return None
            return cmd + ["open", url]
        if action == "snapshot":
            return cmd + ["snapshot", "-i"]
        if action == "click":
            if not target:
                return None
            return cmd + ["click", target]
        if action == "fill":
            if not target:
                return None
            return cmd + ["fill", target, value]
        if action == "extract":
            if not target:
                return None
            selected_mode = mode or "text"
            if selected_mode == "attr":
                if not attribute:
                    return None
                return cmd + ["get", "attr", target, attribute]
            return cmd + ["get", selected_mode, target]
        if action == "screenshot":
            return cmd + (["screenshot", path] if path else ["screenshot"])
        if action == "close":
            return cmd + ["close"]
        return None

    async def _run(self, command: list[str]) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return "Error: agent-browser is not installed. Install agent-browser and run `agent-browser install`."
        except Exception as exc:
            return f"Error starting agent-browser: {exc}"

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
            return f"Error: agent-browser timed out after {self.timeout} seconds"

        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        stdout_text = stdout.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            detail = stderr_text or stdout_text or f"exit code {process.returncode}"
            return f"Error: agent-browser failed: {detail}"

        if not stdout_text:
            return stderr_text or "(no output)"

        return self._normalize_output(stdout_text)

    def _normalize_output(self, stdout_text: str) -> str:
        try:
            payload = json.loads(stdout_text)
        except json.JSONDecodeError:
            return stdout_text

        if not isinstance(payload, dict):
            return stdout_text

        if payload.get("success") is False:
            error = payload.get("error") or payload.get("message") or "unknown error"
            return f"Error: {error}"

        data = payload.get("data")
        if data is None:
            return stdout_text
        if isinstance(data, str):
            return data
        if isinstance(data, (int, float, bool)):
            return str(data)
        if isinstance(data, list):
            return json.dumps(data, ensure_ascii=False, indent=2)
        if not isinstance(data, dict):
            return str(data)

        parts: list[str] = []
        if snapshot := data.get("snapshot"):
            parts.append(str(snapshot))
        if refs := data.get("refs"):
            parts.append(json.dumps(refs, ensure_ascii=False, indent=2))
        if not parts:
            parts.append(json.dumps(data, ensure_ascii=False, indent=2))
        return "\n".join(parts)

    async def execute(
        self,
        action: str,
        url: str = "",
        target: str = "",
        value: str = "",
        mode: str = "text",
        attribute: str = "",
        path: str = "",
        **kwargs: Any,
    ) -> str:
        if action not in self._ACTIONS:
            return f"Error: unsupported action '{action}'"

        command = self._build_command(action, url, target, value, mode, attribute, path)
        if not command:
            return f"Error: missing required parameters for '{action}'"

        return await self._run(command)
