import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from nanobot.cli.commands import app
from nanobot.config.schema import Config
from nanobot.knowledge.service import CaptureResult
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.providers.openai_codex_provider import _strip_model_prefix
from nanobot.providers.registry import find_by_model

runner = CliRunner()


@pytest.fixture
def mock_paths():
    """Mock config/workspace paths for test isolation."""
    with patch("nanobot.config.loader.get_config_path") as mock_cp, \
         patch("nanobot.config.loader.save_config") as mock_sc, \
         patch("nanobot.config.loader.load_config") as mock_lc, \
         patch("nanobot.utils.helpers.get_workspace_path") as mock_ws:

        base_dir = Path("./test_onboard_data")
        if base_dir.exists():
            shutil.rmtree(base_dir)
        base_dir.mkdir()

        config_file = base_dir / "config.json"
        workspace_dir = base_dir / "workspace"

        mock_cp.return_value = config_file
        mock_ws.return_value = workspace_dir
        mock_sc.side_effect = lambda config: config_file.write_text("{}")

        yield config_file, workspace_dir

        if base_dir.exists():
            shutil.rmtree(base_dir)


def test_onboard_fresh_install(mock_paths):
    """No existing config — should create from scratch."""
    config_file, workspace_dir = mock_paths

    result = runner.invoke(app, ["onboard"])

    assert result.exit_code == 0
    assert "Created config" in result.stdout
    assert "Created workspace" in result.stdout
    assert "nanobot is ready" in result.stdout
    assert config_file.exists()
    assert (workspace_dir / "AGENTS.md").exists()
    assert (workspace_dir / "memory" / "MEMORY.md").exists()
    assert (workspace_dir / "inbox").exists()
    assert (workspace_dir / "entities").exists()
    assert (workspace_dir / "ledgers").exists()
    assert (workspace_dir / "indexes").exists()


def test_onboard_existing_config_refresh(mock_paths):
    """Config exists, user declines overwrite — should refresh (load-merge-save)."""
    config_file, workspace_dir = mock_paths
    config_file.write_text('{"existing": true}')

    result = runner.invoke(app, ["onboard"], input="n\n")

    assert result.exit_code == 0
    assert "Config already exists" in result.stdout
    assert "existing values preserved" in result.stdout
    assert workspace_dir.exists()
    assert (workspace_dir / "AGENTS.md").exists()


def test_onboard_existing_config_overwrite(mock_paths):
    """Config exists, user confirms overwrite — should reset to defaults."""
    config_file, workspace_dir = mock_paths
    config_file.write_text('{"existing": true}')

    result = runner.invoke(app, ["onboard"], input="y\n")

    assert result.exit_code == 0
    assert "Config already exists" in result.stdout
    assert "Config reset to defaults" in result.stdout
    assert workspace_dir.exists()


def test_onboard_existing_workspace_safe_create(mock_paths):
    """Workspace exists — should not recreate, but still add missing templates."""
    config_file, workspace_dir = mock_paths
    workspace_dir.mkdir(parents=True)
    config_file.write_text("{}")

    result = runner.invoke(app, ["onboard"], input="n\n")

    assert result.exit_code == 0
    assert "Created workspace" not in result.stdout
    assert "Created AGENTS.md" in result.stdout
    assert (workspace_dir / "AGENTS.md").exists()


def test_config_matches_github_copilot_codex_with_hyphen_prefix():
    config = Config()
    config.agents.defaults.model = "github-copilot/gpt-5.3-codex"

    assert config.get_provider_name() == "github_copilot"


def test_config_matches_openai_codex_with_hyphen_prefix():
    config = Config()
    config.agents.defaults.model = "openai-codex/gpt-5.1-codex"

    assert config.get_provider_name() == "openai_codex"


def test_find_by_model_prefers_explicit_prefix_over_generic_codex_keyword():
    spec = find_by_model("github-copilot/gpt-5.3-codex")

    assert spec is not None
    assert spec.name == "github_copilot"


def test_litellm_provider_canonicalizes_github_copilot_hyphen_prefix():
    provider = LiteLLMProvider(default_model="github-copilot/gpt-5.3-codex")

    resolved = provider._resolve_model("github-copilot/gpt-5.3-codex")

    assert resolved == "github_copilot/gpt-5.3-codex"


def test_openai_codex_strip_prefix_supports_hyphen_and_underscore():
    assert _strip_model_prefix("openai-codex/gpt-5.1-codex") == "gpt-5.1-codex"
    assert _strip_model_prefix("openai_codex/gpt-5.1-codex") == "gpt-5.1-codex"


def test_capture_text_command_uses_knowledge_service(tmp_path):
    class FakeService:
        async def capture_text(self, content_text, *, user_hint="", source="local"):
            assert content_text == "Bike invoice"
            assert user_hint == "bike"
            assert source == "cli"
            return CaptureResult(
                inbox_item_path=tmp_path / "item",
                entities=["personal/bike"],
                actions=["saved original"],
            )

    config = Config.model_validate({})
    config.agents.defaults.workspace = str(tmp_path)

    with patch("nanobot.config.loader.load_config", return_value=config), \
         patch("nanobot.cli.commands._make_knowledge_service", return_value=FakeService()):
        result = runner.invoke(app, ["capture", "text", "Bike invoice", "--hint", "bike"])

    assert result.exit_code == 0
    assert "personal/bike" in result.stdout


def test_capture_file_command_uses_knowledge_service(tmp_path):
    class FakeService:
        async def capture_file(self, file_path, *, user_hint="", source="local", content_text=""):
            assert file_path.name == "invoice.pdf"
            assert user_hint == "bike"
            assert source == "cli"
            return CaptureResult(
                inbox_item_path=tmp_path / "item",
                entities=["personal/bike"],
                actions=["saved original"],
            )

    config = Config.model_validate({})
    config.agents.defaults.workspace = str(tmp_path)
    artifact = tmp_path / "invoice.pdf"
    artifact.write_text("stub", encoding="utf-8")

    with patch("nanobot.config.loader.load_config", return_value=config), \
         patch("nanobot.cli.commands._make_knowledge_service", return_value=FakeService()):
        result = runner.invoke(app, ["capture", "file", str(artifact), "--hint", "bike"])

    assert result.exit_code == 0
    assert "personal/bike" in result.stdout


def test_gateway_starts_native_capture_server_when_enabled(tmp_path):
    class FakeAgentLoop:
        def __init__(self, *args, **kwargs):
            self.knowledge_service = object()

        async def run(self):
            return None

        async def close_mcp(self):
            return None

        def stop(self):
            return None

        async def process_direct(self, *args, **kwargs):
            return ""

    class FakeChannelManager:
        def __init__(self, *args, **kwargs):
            self.enabled_channels = []

        async def start_all(self):
            return None

        async def stop_all(self):
            return None

    class FakeCronService:
        def __init__(self, *args, **kwargs):
            self.on_job = None

        def status(self):
            return {"jobs": 0}

        async def start(self):
            return None

        def stop(self):
            return None

    class FakeHeartbeatService:
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            return None

        def stop(self):
            return None

    class FakeNativeCaptureServer:
        started = False
        stopped = False
        kwargs = {}

        def __init__(self, **kwargs):
            type(self).kwargs = kwargs

        def start(self):
            type(self).started = True

        def stop(self):
            type(self).stopped = True

    config = Config.model_validate({})
    config.agents.defaults.workspace = str(tmp_path)
    config.knowledge.local_web.enabled = False
    config.knowledge.native_capture.enabled = True
    config.knowledge.native_capture.bind = "127.0.0.1"
    config.knowledge.native_capture.port = 18792
    config.knowledge.native_capture.auth_token = "native-secret"

    with patch("nanobot.config.loader.load_config", return_value=config), \
         patch("nanobot.config.loader.get_data_dir", return_value=tmp_path), \
         patch("nanobot.cli.commands._make_provider", return_value=object()), \
         patch("nanobot.bus.queue.MessageBus"), \
         patch("nanobot.agent.loop.AgentLoop", FakeAgentLoop), \
         patch("nanobot.channels.manager.ChannelManager", FakeChannelManager), \
         patch("nanobot.session.manager.SessionManager"), \
         patch("nanobot.cron.service.CronService", FakeCronService), \
         patch("nanobot.heartbeat.service.HeartbeatService", FakeHeartbeatService), \
         patch("nanobot.knowledge.native_inbox.NativeCaptureServer", FakeNativeCaptureServer):
        result = runner.invoke(app, ["gateway"])

    assert result.exit_code == 0
    assert "Native capture endpoint: http://127.0.0.1:18792/capture" in result.stdout
    assert FakeNativeCaptureServer.kwargs["auth_token"] == "native-secret"
    assert FakeNativeCaptureServer.started is True
    assert FakeNativeCaptureServer.stopped is True
