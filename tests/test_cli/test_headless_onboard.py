"""Tests for headless (non-interactive) onboarding."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.cli.onboard import _headless_channels, run_headless_onboarding


class TestHeadlessChannels:
    def test_no_env_vars(self):
        with patch.dict("os.environ", {}, clear=True):
            cfg = _headless_channels()
            assert cfg.telegram_enabled is False
            assert cfg.whatsapp_enabled is False

    def test_telegram_enabled(self):
        with patch.dict("os.environ", {
            "TELEGRAM_TOKEN": "bot123:abc",
            "TELEGRAM_CHAT_ID": "456",
        }, clear=True):
            cfg = _headless_channels()
            assert cfg.telegram_enabled is True
            assert cfg.telegram_bot_token == "bot123:abc"
            assert cfg.telegram_chat_id == "456"

    def test_whatsapp_enabled(self):
        with patch.dict("os.environ", {
            "WHATSAPP_ACCESS_TOKEN": "wa-token",
            "WHATSAPP_PHONE_NUMBER_ID": "12345",
            "WHATSAPP_VERIFY_TOKEN": "my-verify",
        }, clear=True):
            cfg = _headless_channels()
            assert cfg.whatsapp_enabled is True
            assert cfg.whatsapp_access_token == "wa-token"
            assert cfg.whatsapp_phone_number_id == "12345"
            assert cfg.whatsapp_verify_token == "my-verify"

    def test_whatsapp_needs_both_fields(self):
        """WhatsApp requires both access token AND phone number ID."""
        with patch.dict("os.environ", {
            "WHATSAPP_ACCESS_TOKEN": "wa-token",
        }, clear=True):
            cfg = _headless_channels()
            assert cfg.whatsapp_enabled is False

    def test_both_channels(self):
        with patch.dict("os.environ", {
            "TELEGRAM_TOKEN": "bot",
            "WHATSAPP_ACCESS_TOKEN": "wa",
            "WHATSAPP_PHONE_NUMBER_ID": "123",
        }, clear=True):
            cfg = _headless_channels()
            assert cfg.telegram_enabled is True
            assert cfg.whatsapp_enabled is True


class TestRunHeadlessOnboarding:
    @patch("vandelay.cli.onboard.init_workspace")
    def test_default_anthropic(self, mock_init_ws, tmp_path):
        mock_init_ws.return_value = tmp_path / "workspace"

        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "sk-test-key",
        }, clear=True):
            with patch.object(
                __import__("vandelay.config.settings", fromlist=["Settings"]).Settings,
                "save",
            ):
                settings = run_headless_onboarding()
                assert settings.model.provider == "anthropic"
                assert settings.agent_name == "Art"
                assert settings.timezone == "UTC"
                assert settings.safety.mode == "confirm"

    @patch("vandelay.cli.onboard.init_workspace")
    def test_custom_values(self, mock_init_ws, tmp_path):
        mock_init_ws.return_value = tmp_path / "workspace"

        with patch.dict("os.environ", {
            "VANDELAY_MODEL_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-openai",
            "VANDELAY_AGENT_NAME": "CustomBot",
            "VANDELAY_TIMEZONE": "US/Pacific",
            "VANDELAY_SAFETY_MODE": "trust",
            "VANDELAY_USER_ID": "user@test.com",
            "VANDELAY_KNOWLEDGE_ENABLED": "true",
        }, clear=True):
            with patch.object(
                __import__("vandelay.config.settings", fromlist=["Settings"]).Settings,
                "save",
            ):
                settings = run_headless_onboarding()
                assert settings.model.provider == "openai"
                assert settings.agent_name == "CustomBot"
                assert settings.timezone == "US/Pacific"
                assert settings.safety.mode == "trust"
                assert settings.user_id == "user@test.com"
                assert settings.knowledge.enabled is True

    def test_unknown_provider_raises(self):
        with patch.dict("os.environ", {
            "VANDELAY_MODEL_PROVIDER": "nonexistent_provider",
        }, clear=True):
            with pytest.raises(ValueError, match="Unknown provider"):
                run_headless_onboarding()

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {
            "VANDELAY_MODEL_PROVIDER": "anthropic",
        }, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY must be set"):
                run_headless_onboarding()

    @patch("vandelay.cli.onboard.init_workspace")
    def test_ollama_no_api_key_needed(self, mock_init_ws, tmp_path):
        """Ollama doesn't require an API key."""
        mock_init_ws.return_value = tmp_path / "workspace"

        with patch.dict("os.environ", {
            "VANDELAY_MODEL_PROVIDER": "ollama",
        }, clear=True):
            with patch.object(
                __import__("vandelay.config.settings", fromlist=["Settings"]).Settings,
                "save",
            ):
                settings = run_headless_onboarding()
                assert settings.model.provider == "ollama"

    @patch("vandelay.cli.onboard.init_workspace")
    def test_openrouter_provider(self, mock_init_ws, tmp_path):
        mock_init_ws.return_value = tmp_path / "workspace"

        with patch.dict("os.environ", {
            "VANDELAY_MODEL_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-test",
        }, clear=True):
            with patch.object(
                __import__("vandelay.config.settings", fromlist=["Settings"]).Settings,
                "save",
            ):
                settings = run_headless_onboarding()
                assert settings.model.provider == "openrouter"
                assert settings.model.model_id == "anthropic/claude-sonnet-4-5-20250929"

    @patch("vandelay.cli.onboard.init_workspace")
    def test_knowledge_disabled_by_default(self, mock_init_ws, tmp_path):
        mock_init_ws.return_value = tmp_path / "workspace"

        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "sk-test",
        }, clear=True):
            with patch.object(
                __import__("vandelay.config.settings", fromlist=["Settings"]).Settings,
                "save",
            ):
                settings = run_headless_onboarding()
                assert settings.knowledge.enabled is False
