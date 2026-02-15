"""Tests for Google Calendar tool wiring in ToolManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import GoogleConfig, ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.tools.manager import ToolManager
from vandelay.tools.registry import ToolRegistry


@pytest.fixture
def tmp_manager(tmp_path: Path) -> ToolManager:
    """Manager with a fresh registry cache."""
    registry = ToolRegistry(cache_path=tmp_path / "tool_registry.json")
    registry.refresh()
    return ToolManager(registry=registry)


@pytest.fixture
def google_settings(tmp_path: Path) -> Settings:
    """Settings with Google config and googlecalendar enabled."""
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="tiered"),
        workspace_dir=str(tmp_path / "workspace"),
        google=GoogleConfig(calendar_id="shared@example.com"),
        enabled_tools=["googlecalendar"],
        db_url="",
    )


class TestGoogleCalendarWiring:
    """Verify calendar_id and allow_update are passed to GoogleCalendarTools."""

    def test_calendar_id_passed(self, tmp_manager: ToolManager, google_settings: Settings):
        """GoogleCalendarTools should receive calendar_id from settings."""
        import importlib

        from vandelay.config.settings import get_settings

        mock_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.GoogleCalendarTools = mock_cls

        entry = tmp_manager.registry.get("googlecalendar")
        if entry is None:
            pytest.skip("googlecalendar not in registry")

        # Only mock the calendar module import, let others through
        real_import = importlib.import_module
        calendar_module = entry.module_path

        def selective_import(name, *args, **kwargs):
            if name == calendar_module:
                return mock_module
            return real_import(name, *args, **kwargs)

        # Clear the lru_cache so our mock can take effect
        get_settings.cache_clear()

        with (
            patch("importlib.import_module", side_effect=selective_import),
            patch(
                "vandelay.config.settings.get_settings",
                return_value=google_settings,
            ),
        ):
            instances = tmp_manager.instantiate_tools(
                ["googlecalendar"], settings=google_settings,
            )

        # The constructor should have been called with calendar_id and allow_update
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["calendar_id"] == "shared@example.com"
        assert call_kwargs["allow_update"] is True
        assert "https://www.googleapis.com/auth/calendar" in call_kwargs["scopes"]

        # Restore cache for other tests
        get_settings.cache_clear()

    def test_default_calendar_id(self, tmp_manager: ToolManager, tmp_path: Path):
        """Default calendar_id should be 'primary'."""
        settings = Settings(
            agent_name="TestClaw",
            model=ModelConfig(provider="ollama", model_id="llama3.1"),
            safety=SafetyConfig(mode="tiered"),
            workspace_dir=str(tmp_path / "workspace"),
            enabled_tools=["googlecalendar"],
            db_url="",
        )
        assert settings.google.calendar_id == "primary"


class TestGoogleConfigInSettings:
    """Verify GoogleConfig integrates with Settings properly."""

    def test_settings_has_google_field(self, tmp_path: Path):
        settings = Settings(
            agent_name="Test",
            workspace_dir=str(tmp_path / "ws"),
            db_url="",
        )
        assert hasattr(settings, "google")
        assert isinstance(settings.google, GoogleConfig)
        assert settings.google.calendar_id == "primary"

    def test_settings_custom_google_config(self, tmp_path: Path):
        settings = Settings(
            agent_name="Test",
            workspace_dir=str(tmp_path / "ws"),
            google=GoogleConfig(calendar_id="work@company.com"),
            db_url="",
        )
        assert settings.google.calendar_id == "work@company.com"

    def test_settings_save_roundtrip(self, tmp_path: Path):
        """GoogleConfig should survive save/load roundtrip."""
        import json

        config_file = tmp_path / "config.json"
        settings = Settings(
            agent_name="Test",
            workspace_dir=str(tmp_path / "ws"),
            google=GoogleConfig(calendar_id="test@example.com"),
            db_url="",
        )
        data = settings.model_dump(mode="json")
        config_file.write_text(json.dumps(data, indent=2))

        loaded = json.loads(config_file.read_text())
        assert loaded["google"]["calendar_id"] == "test@example.com"
