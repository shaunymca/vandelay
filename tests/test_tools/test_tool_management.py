"""Tests for the ToolManagementTools agent toolkit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.tools.tool_management import ToolManagementTools


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    config_file = tmp_path / "config.json"
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="tiered"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=["file"],
        db_url="",
    )


@pytest.fixture
def reload_tracker() -> dict:
    return {"count": 0}


@pytest.fixture
def toolkit(test_settings: Settings, reload_tracker: dict) -> ToolManagementTools:
    def _reload():
        reload_tracker["count"] += 1

    return ToolManagementTools(settings=test_settings, reload_callback=_reload)


def test_list_available_tools_returns_text(toolkit: ToolManagementTools):
    """list_available_tools should return formatted markdown text."""
    result = toolkit.list_available_tools()
    assert "Available Tools" in result
    assert "file" in result.lower()


def test_list_available_tools_shows_enabled(toolkit: ToolManagementTools):
    """Enabled tools should be marked in the listing."""
    result = toolkit.list_available_tools()
    # "file" is enabled in test_settings
    assert "[enabled]" in result


def test_get_tool_info_known_tool(toolkit: ToolManagementTools):
    """get_tool_info should return details for a known tool."""
    result = toolkit.get_tool_info("shell")
    assert "shell" in result.lower()
    assert "ShellTools" in result
    assert "Category" in result


def test_get_tool_info_unknown_tool(toolkit: ToolManagementTools):
    """get_tool_info should return an error for an unknown tool."""
    result = toolkit.get_tool_info("nonexistent_xyz")
    assert "Unknown tool" in result


def test_get_tool_info_shows_enabled_status(toolkit: ToolManagementTools):
    """get_tool_info should show enabled status correctly."""
    result = toolkit.get_tool_info("file")
    assert "yes" in result.lower()  # enabled: yes

    result2 = toolkit.get_tool_info("shell")
    # shell is not in enabled_tools
    assert "Enabled**: no" in result2


def test_enable_tool_success(
    toolkit: ToolManagementTools,
    test_settings: Settings,
    reload_tracker: dict,
):
    """enable_tool should add to enabled_tools and trigger reload."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.enable_tool("calculator")

    assert "enabled" in result.lower()
    assert "calculator" in test_settings.enabled_tools
    assert reload_tracker["count"] == 1


def test_enable_tool_already_enabled(toolkit: ToolManagementTools):
    """enable_tool should report if tool is already enabled."""
    result = toolkit.enable_tool("file")  # already in enabled_tools
    assert "already enabled" in result.lower()


def test_enable_tool_unknown(toolkit: ToolManagementTools):
    """enable_tool should fail for unknown tools."""
    result = toolkit.enable_tool("totally_fake_tool_xyz")
    assert "Unknown tool" in result


def test_disable_tool_success(
    toolkit: ToolManagementTools,
    test_settings: Settings,
    reload_tracker: dict,
):
    """disable_tool should remove from enabled_tools and trigger reload."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.disable_tool("file")

    assert "disabled" in result.lower()
    assert "file" not in test_settings.enabled_tools
    assert reload_tracker["count"] == 1


def test_disable_tool_not_enabled(toolkit: ToolManagementTools):
    """disable_tool should report if tool is not currently enabled."""
    result = toolkit.disable_tool("shell")  # not in enabled_tools
    assert "not currently enabled" in result.lower()


def test_enable_tool_with_deps_installs(
    toolkit: ToolManagementTools,
    test_settings: Settings,
    reload_tracker: dict,
):
    """enable_tool for a tool with deps should call install_deps."""
    with (
        patch.object(Settings, "save", return_value=None),
        patch(
            "vandelay.tools.tool_management.ToolManager.install_deps"
        ) as mock_install,
    ):
        from vandelay.tools.manager import InstallResult
        mock_install.return_value = InstallResult(True, "Installed: ddgs", "duckduckgo")
        result = toolkit.enable_tool("duckduckgo")

    assert "enabled" in result.lower()
    mock_install.assert_called_once_with("duckduckgo")


def test_enable_tool_install_failure(
    toolkit: ToolManagementTools,
    test_settings: Settings,
):
    """enable_tool should report failure when deps can't be installed."""
    with patch(
        "vandelay.tools.tool_management.ToolManager.install_deps"
    ) as mock_install:
        from vandelay.tools.manager import InstallResult
        mock_install.return_value = InstallResult(False, "uv not found", "duckduckgo")
        result = toolkit.enable_tool("duckduckgo")

    assert "failed" in result.lower()
    assert "duckduckgo" not in test_settings.enabled_tools
