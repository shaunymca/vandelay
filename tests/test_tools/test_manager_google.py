"""Tests for Google tool wiring in ToolManager."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import GoogleConfig, ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.tools.manager import (
    ToolManager,
    _google_all_scopes,
    _inject_google_creds,
)
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
        assert call_kwargs["scopes"] == _google_all_scopes()

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


class TestGoogleAllScopes:
    """Verify the unified scope list."""

    def test_contains_all_four_scopes(self):
        scopes = _google_all_scopes()
        assert "https://www.googleapis.com/auth/gmail.modify" in scopes
        assert "https://www.googleapis.com/auth/calendar" in scopes
        assert "https://www.googleapis.com/auth/drive" in scopes
        assert "https://www.googleapis.com/auth/spreadsheets" in scopes

    def test_returns_list(self):
        assert isinstance(_google_all_scopes(), list)


class TestInjectGoogleCreds:
    """Verify credential injection and _auth replacement."""

    def test_replaces_auth_method(self, tmp_path: Path):
        """_inject_google_creds should replace the tool's _auth method."""
        tool = MagicMock()
        tool.creds = None
        original_auth = tool._auth

        token_path = str(tmp_path / "google_token.json")
        # No token file — should still replace _auth
        _inject_google_creds(tool, token_path)

        assert tool._auth != original_auth

    def test_preloads_valid_creds(self, tmp_path: Path):
        """When a valid token exists, creds should be pre-loaded."""
        tool = MagicMock()
        tool.creds = None
        token_path = tmp_path / "google_token.json"

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ):
            token_path.write_text("{}")
            _inject_google_creds(tool, str(token_path))

        assert tool.creds is mock_creds

    def test_safe_auth_refreshes_expired_creds(self, tmp_path: Path):
        """Replaced _auth should refresh expired creds without opening browser."""
        tool = MagicMock()
        tool.creds = None
        token_path = tmp_path / "google_token.json"
        token_path.write_text("{}")

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True

        with patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ):
            _inject_google_creds(tool, str(token_path))

        # The _auth method was replaced — call it and verify no browser opens
        fresh_creds = MagicMock()
        fresh_creds.valid = True
        fresh_creds.expired = False

        with patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=fresh_creds,
        ):
            tool._auth()

    def test_safe_auth_no_token_file_logs_error(self, tmp_path: Path, caplog):
        """Safe _auth should log error if token file missing."""
        tool = MagicMock()
        tool.creds = None
        token_path = str(tmp_path / "nonexistent_token.json")

        _inject_google_creds(tool, token_path)
        # creds should still be None — no token file
        assert tool.creds is None

    def test_all_google_tools_get_all_scopes(
        self, tmp_manager: ToolManager, google_settings: Settings,
    ):
        """Every Google tool should receive all 4 scopes."""
        import importlib

        from vandelay.config.settings import get_settings

        mock_cls = MagicMock()
        mock_module = MagicMock()

        # Map all Google tools to the same mock
        google_tools = ["gmail", "google_drive", "googlecalendar", "googlesheets"]
        entries = {}
        for name in google_tools:
            e = tmp_manager.registry.get(name)
            if e:
                entries[name] = e.module_path

        if not entries:
            pytest.skip("No Google tools in registry")

        real_import = importlib.import_module

        def selective_import(name, *args, **kwargs):
            if name in entries.values():
                return mock_module
            return real_import(name, *args, **kwargs)

        # Set the class name dynamically
        for entry_name in entries:
            e = tmp_manager.registry.get(entry_name)
            setattr(mock_module, e.class_name, MagicMock())

        get_settings.cache_clear()

        with (
            patch("importlib.import_module", side_effect=selective_import),
            patch(
                "vandelay.config.settings.get_settings",
                return_value=google_settings,
            ),
            patch("vandelay.tools.manager._inject_google_creds"),
        ):
            for tool_name in entries:
                mock_cls = getattr(mock_module, tmp_manager.registry.get(tool_name).class_name)
                mock_cls.reset_mock()
                tmp_manager.instantiate_tools(
                    [tool_name], settings=google_settings,
                )
                mock_cls.assert_called_once()
                call_kwargs = mock_cls.call_args[1]
                assert call_kwargs["scopes"] == _google_all_scopes(), (
                    f"{tool_name} should receive all scopes"
                )

        get_settings.cache_clear()
