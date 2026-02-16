"""Tests for the redesigned 3-step onboarding flow."""

from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import KnowledgeConfig, ModelConfig
from vandelay.config.settings import Settings


class TestRunOnboarding:
    """Tests for the new run_onboarding() 3-step flow."""

    @patch("vandelay.cli.onboard._write_env_key")
    @patch("vandelay.cli.onboard._populate_user_md")
    @patch("vandelay.cli.onboard._detect_system_timezone", return_value="US/Eastern")
    @patch("vandelay.cli.onboard.init_workspace")
    @patch("vandelay.cli.onboard.questionary")
    def test_happy_path_anthropic(
        self, mock_q, mock_ws, mock_tz, mock_populate, mock_write_env, tmp_path
    ):
        """Full onboarding: provider → API key → model (live fetch)."""
        from vandelay.cli.onboard import run_onboarding

        mock_ws.return_value = tmp_path / "workspace"
        (tmp_path / "workspace").mkdir()

        # questionary.select: provider, then model
        select_mock = MagicMock()
        select_mock.ask.side_effect = [
            "anthropic",                      # Step 1: provider
            "claude-sonnet-4-5-20250929",     # Step 3: model
        ]
        mock_q.select.return_value = select_mock

        # questionary.password for API key (Step 2)
        password_mock = MagicMock()
        password_mock.ask.return_value = "sk-test-key"
        mock_q.password.return_value = password_mock

        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        with (
            patch("vandelay.config.constants.CONFIG_FILE", tmp_path / "nonexistent.json"),
            patch("vandelay.cli.onboard.fetch_provider_models", return_value=[]),
            patch.object(Settings, "save"),
            patch("vandelay.cli.banner.print_banner"),
        ):
            settings = run_onboarding()

        assert settings.model.provider == "anthropic"
        assert settings.model.model_id == "claude-sonnet-4-5-20250929"
        assert settings.agent_name == "Art"
        assert settings.timezone == "US/Eastern"
        assert settings.knowledge.enabled is True
        assert settings.enabled_tools == ["shell", "file", "python"]
        assert settings.safety.mode == "confirm"

    @patch("vandelay.cli.onboard._populate_user_md")
    @patch("vandelay.cli.onboard._detect_system_timezone", return_value=None)
    @patch("vandelay.cli.onboard.init_workspace")
    @patch("vandelay.cli.onboard.questionary")
    def test_ollama_skips_api_key(
        self, mock_q, mock_ws, mock_tz, mock_populate, tmp_path
    ):
        """Ollama provider should skip the API key step."""
        from vandelay.cli.onboard import run_onboarding

        mock_ws.return_value = tmp_path / "workspace"
        (tmp_path / "workspace").mkdir()

        # questionary.select: provider, model
        select_mock = MagicMock()
        select_mock.ask.side_effect = ["ollama", "llama3.1"]
        mock_q.select.return_value = select_mock

        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        with (
            patch("vandelay.config.constants.CONFIG_FILE", tmp_path / "nonexistent.json"),
            patch("vandelay.cli.onboard.fetch_ollama_models", return_value=[]),
            patch.object(Settings, "save"),
            patch("vandelay.cli.banner.print_banner"),
        ):
            settings = run_onboarding()

        assert settings.model.provider == "ollama"
        assert settings.model.model_id == "llama3.1"
        assert settings.timezone == "UTC"
        # password should NOT have been called (Ollama has no env_key)
        mock_q.password.assert_not_called()

    @patch("vandelay.cli.onboard.questionary")
    def test_rerun_detection_aborts(self, mock_q, tmp_path):
        """If config exists and user declines reconfigure, raises KeyboardInterrupt."""
        from vandelay.cli.onboard import run_onboarding

        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        confirm_mock = MagicMock()
        confirm_mock.ask.return_value = False
        mock_q.confirm.return_value = confirm_mock

        with patch("vandelay.config.constants.CONFIG_FILE", config_file):
            with pytest.raises(KeyboardInterrupt):
                run_onboarding()


class TestSelectModel:
    """Tests for _select_model() helper."""

    @patch("vandelay.cli.onboard.questionary")
    def test_select_from_catalog(self, mock_q):
        from vandelay.cli.onboard import _select_model

        select_mock = MagicMock()
        select_mock.ask.return_value = "gpt-4o"
        mock_q.select.return_value = select_mock
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        result = _select_model("openai")
        assert result == "gpt-4o"

    @patch("vandelay.cli.onboard.questionary")
    def test_select_other_custom_model(self, mock_q):
        from vandelay.cli.onboard import _select_model

        select_mock = MagicMock()
        select_mock.ask.return_value = "_other"
        mock_q.select.return_value = select_mock

        text_mock = MagicMock()
        text_mock.ask.return_value = "gpt-4-turbo"
        mock_q.text.return_value = text_mock

        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        result = _select_model("openai")
        assert result == "gpt-4-turbo"

    @patch("vandelay.cli.onboard.fetch_provider_models")
    @patch("vandelay.cli.onboard.questionary")
    def test_live_fetch_with_api_key(self, mock_q, mock_fetch):
        """When API key is provided, live-fetched models are shown."""
        from vandelay.models.catalog import ModelOption
        from vandelay.cli.onboard import _select_model

        mock_fetch.return_value = [
            ModelOption("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5", "api"),
            ModelOption("claude-opus-4-5-20250929", "Claude Opus 4.5", "api"),
        ]
        select_mock = MagicMock()
        select_mock.ask.return_value = "claude-opus-4-5-20250929"
        mock_q.select.return_value = select_mock
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        result = _select_model("anthropic", api_key="sk-test")
        assert result == "claude-opus-4-5-20250929"
        mock_fetch.assert_called_once_with("anthropic", "sk-test", timeout=3.0)

    @patch("vandelay.cli.onboard.fetch_provider_models")
    @patch("vandelay.cli.onboard.questionary")
    def test_live_fetch_failure_falls_back(self, mock_q, mock_fetch):
        """When live fetch fails, falls back to curated catalog."""
        from vandelay.cli.onboard import _select_model

        mock_fetch.return_value = []  # Fetch failed
        select_mock = MagicMock()
        select_mock.ask.return_value = "gpt-4o"
        mock_q.select.return_value = select_mock
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        result = _select_model("openai", api_key="sk-test")
        assert result == "gpt-4o"

    @patch("vandelay.cli.onboard.questionary")
    def test_no_api_key_uses_catalog(self, mock_q):
        """Without API key, uses curated catalog directly."""
        from vandelay.cli.onboard import _select_model

        select_mock = MagicMock()
        select_mock.ask.return_value = "gpt-4o"
        mock_q.select.return_value = select_mock
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        with patch("vandelay.cli.onboard.fetch_provider_models") as mock_fetch:
            result = _select_model("openai", api_key=None)
            mock_fetch.assert_not_called()
        assert result == "gpt-4o"

    @patch("vandelay.cli.onboard.fetch_ollama_models")
    @patch("vandelay.cli.onboard.questionary")
    def test_ollama_live_fetch(self, mock_q, mock_fetch):
        from vandelay.models.catalog import ModelOption
        from vandelay.cli.onboard import _select_model

        mock_fetch.return_value = [
            ModelOption("llama3.1:latest", "llama3.1:latest", "local"),
            ModelOption("codellama:7b", "codellama:7b", "local"),
        ]
        select_mock = MagicMock()
        select_mock.ask.return_value = "llama3.1:latest"
        mock_q.select.return_value = select_mock
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        result = _select_model("ollama")
        assert result == "llama3.1:latest"

    @patch("vandelay.cli.onboard.fetch_ollama_models")
    @patch("vandelay.cli.onboard.questionary")
    def test_ollama_server_down_fallback(self, mock_q, mock_fetch):
        """When Ollama server is unreachable, falls back to curated catalog."""
        from vandelay.cli.onboard import _select_model

        mock_fetch.return_value = []  # Server unreachable
        select_mock = MagicMock()
        select_mock.ask.return_value = "llama3.1"
        mock_q.select.return_value = select_mock
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)

        result = _select_model("ollama")
        assert result == "llama3.1"


class TestConfigureAuthQuick:
    """Tests for _configure_auth_quick() helper."""

    @patch("vandelay.cli.onboard._write_env_key")
    @patch("vandelay.cli.onboard.questionary")
    def test_saves_api_key_returns_value(self, mock_q, mock_write_env):
        import os
        from vandelay.cli.onboard import _configure_auth_quick

        env_backup = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            password_mock = MagicMock()
            password_mock.ask.return_value = "sk-test"
            mock_q.password.return_value = password_mock

            result = _configure_auth_quick("anthropic")
            assert result == "sk-test"
            mock_write_env.assert_called_once_with("ANTHROPIC_API_KEY", "sk-test")
            assert os.environ.get("ANTHROPIC_API_KEY") == "sk-test"
        finally:
            if env_backup:
                os.environ["ANTHROPIC_API_KEY"] = env_backup
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_returns_existing_env_key(self):
        import os
        from vandelay.cli.onboard import _configure_auth_quick

        env_backup = os.environ.get("ANTHROPIC_API_KEY")
        try:
            os.environ["ANTHROPIC_API_KEY"] = "sk-existing"
            result = _configure_auth_quick("anthropic")
            assert result == "sk-existing"
        finally:
            if env_backup:
                os.environ["ANTHROPIC_API_KEY"] = env_backup
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_ollama_returns_none(self):
        from vandelay.cli.onboard import _configure_auth_quick

        result = _configure_auth_quick("ollama")
        assert result is None


class TestSmartDefaults:
    """Verify the new default values are correct."""

    def test_knowledge_enabled_by_default(self):
        cfg = KnowledgeConfig()
        assert cfg.enabled is True

    def test_enabled_tools_default(self):
        field_info = Settings.model_fields["enabled_tools"]
        default = field_info.default_factory()
        assert default == ["shell", "file", "python"]
