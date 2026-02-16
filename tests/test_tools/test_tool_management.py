"""Tests for the ToolManagementTools agent toolkit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import MemberConfig, ModelConfig, SafetyConfig, TeamConfig
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


# --- Tool assignment tests ---


@pytest.fixture
def team_settings(tmp_path: Path) -> Settings:
    config_file = tmp_path / "config.json"
    return Settings(
        agent_name="TestTeam",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="tiered"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=["shell", "file", "tavily"],
        team=TeamConfig(
            enabled=True,
            members=[
                MemberConfig(name="cto", role="Tech lead", tools=["shell"]),
                MemberConfig(name="research", role="Researcher", tools=["tavily"]),
                "browser",  # legacy string member
            ],
        ),
        db_url="",
    )


@pytest.fixture
def team_toolkit(team_settings: Settings, reload_tracker: dict) -> ToolManagementTools:
    def _reload():
        reload_tracker["count"] += 1

    return ToolManagementTools(settings=team_settings, reload_callback=_reload)


def test_assign_tool_success(
    team_toolkit: ToolManagementTools,
    team_settings: Settings,
    reload_tracker: dict,
):
    """assign_tool_to_member should add tool and trigger reload."""
    with patch.object(Settings, "save", return_value=None):
        result = team_toolkit.assign_tool_to_member("file", "cto")

    assert "assigned" in result.lower()
    # Find cto member and check tool was added
    for m in team_settings.team.members:
        if isinstance(m, MemberConfig) and m.name == "cto":
            assert "file" in m.tools
            break
    assert reload_tracker["count"] == 1


def test_assign_tool_already_has(team_toolkit: ToolManagementTools):
    """assign_tool_to_member should report if member already has the tool."""
    result = team_toolkit.assign_tool_to_member("shell", "cto")
    assert "already has" in result.lower()


def test_assign_tool_unknown_tool(team_toolkit: ToolManagementTools):
    """assign_tool_to_member should fail for unknown tools."""
    result = team_toolkit.assign_tool_to_member("fake_tool_xyz", "cto")
    assert "Unknown tool" in result


def test_assign_tool_not_enabled(team_toolkit: ToolManagementTools):
    """assign_tool_to_member should fail for tools not globally enabled."""
    result = team_toolkit.assign_tool_to_member("calculator", "cto")
    assert "not globally enabled" in result.lower()


def test_assign_tool_unknown_member(team_toolkit: ToolManagementTools):
    """assign_tool_to_member should fail for unknown members."""
    result = team_toolkit.assign_tool_to_member("shell", "nonexistent")
    assert "Unknown member" in result


def test_assign_tool_resolves_string_member(
    team_toolkit: ToolManagementTools,
    team_settings: Settings,
    reload_tracker: dict,
):
    """assign_tool_to_member should convert string member to MemberConfig."""
    with patch.object(Settings, "save", return_value=None):
        result = team_toolkit.assign_tool_to_member("tavily", "browser")

    assert "assigned" in result.lower()
    # browser should now be a MemberConfig
    browser = team_settings.team.members[2]
    assert isinstance(browser, MemberConfig)
    assert "tavily" in browser.tools


def test_remove_tool_success(
    team_toolkit: ToolManagementTools,
    team_settings: Settings,
    reload_tracker: dict,
):
    """remove_tool_from_member should remove tool and trigger reload."""
    with patch.object(Settings, "save", return_value=None):
        result = team_toolkit.remove_tool_from_member("shell", "cto")

    assert "removed" in result.lower()
    for m in team_settings.team.members:
        if isinstance(m, MemberConfig) and m.name == "cto":
            assert "shell" not in m.tools
            break
    assert reload_tracker["count"] == 1


def test_remove_tool_not_found(team_toolkit: ToolManagementTools):
    """remove_tool_from_member should fail if member doesn't have the tool."""
    result = team_toolkit.remove_tool_from_member("tavily", "cto")
    assert "doesn't have" in result.lower()


def test_remove_tool_unknown_member(team_toolkit: ToolManagementTools):
    """remove_tool_from_member should fail for unknown members."""
    result = team_toolkit.remove_tool_from_member("shell", "nonexistent")
    assert "Unknown member" in result


def test_remove_tool_string_member(team_toolkit: ToolManagementTools):
    """remove_tool_from_member should fail gracefully for string members."""
    result = team_toolkit.remove_tool_from_member("crawl4ai", "browser")
    assert "default tools" in result.lower()


def test_team_tools_registered_when_enabled(team_toolkit: ToolManagementTools):
    """assign/remove functions should be registered when team is enabled."""
    func_names = [f.name for f in team_toolkit.functions.values()]
    assert "assign_tool_to_member" in func_names
    assert "remove_tool_from_member" in func_names


def test_enable_tool_team_hint(
    team_toolkit: ToolManagementTools,
    team_settings: Settings,
):
    """enable_tool should hint about member assignment when team mode is active."""
    with patch.object(Settings, "save", return_value=None):
        result = team_toolkit.enable_tool("calculator")

    assert "assign_tool_to_member" in result
    assert "calculator" in result


def test_enable_tool_no_team_hint(
    toolkit: ToolManagementTools,
    test_settings: Settings,
):
    """enable_tool should NOT hint about member assignment when team is off."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.enable_tool("calculator")

    assert "assign_tool_to_member" not in result


def test_team_tools_not_registered_when_disabled(reload_tracker: dict):
    """assign/remove functions should NOT be registered when team is disabled."""
    settings = Settings(
        agent_name="Test",
        model=ModelConfig(provider="ollama"),
        team=TeamConfig(enabled=False),
        enabled_tools=["shell"],
    )
    tk = ToolManagementTools(
        settings=settings,
        reload_callback=lambda: reload_tracker.__setitem__("count", 0),
    )
    func_names = [f.name for f in tk.functions.values()]
    assert "assign_tool_to_member" not in func_names
    assert "remove_tool_from_member" not in func_names
