"""Tests for the MemberManagementTools agent toolkit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from vandelay.config.models import MemberConfig, ModelConfig, SafetyConfig, TeamConfig
from vandelay.config.settings import Settings
from vandelay.tools.member_management import MemberManagementTools


@pytest.fixture
def team_settings(tmp_path: Path) -> Settings:
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
            ],
        ),
        db_url="",
    )


@pytest.fixture
def empty_team_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestTeam",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=["shell"],
        team=TeamConfig(enabled=True, members=[]),
        db_url="",
    )


@pytest.fixture
def reload_tracker() -> dict:
    return {"count": 0}


@pytest.fixture
def toolkit(team_settings: Settings, reload_tracker: dict) -> MemberManagementTools:
    def _reload():
        reload_tracker["count"] += 1

    return MemberManagementTools(settings=team_settings, reload_callback=_reload)


@pytest.fixture
def empty_toolkit(
    empty_team_settings: Settings, reload_tracker: dict
) -> MemberManagementTools:
    def _reload():
        reload_tracker["count"] += 1

    return MemberManagementTools(settings=empty_team_settings, reload_callback=_reload)


# --- list_team_members ---


def test_list_empty_team(empty_toolkit: MemberManagementTools):
    """Empty team returns a clean message."""
    result = empty_toolkit.list_team_members()
    assert "No team members" in result


def test_list_members(toolkit: MemberManagementTools):
    """Shows name, role, and tools for each member."""
    result = toolkit.list_team_members()
    assert "cto" in result
    assert "Tech lead" in result
    assert "shell" in result
    assert "research" in result
    assert "tavily" in result


# --- add_team_member ---


def test_add_member(toolkit: MemberManagementTools, team_settings: Settings):
    """Creates MemberConfig and appears in settings."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.add_team_member("devops", "DevOps specialist", "shell")

    assert "added" in result.lower()
    names = [m.name for m in team_settings.team.members if isinstance(m, MemberConfig)]
    assert "devops" in names


def test_add_member_with_instructions(
    toolkit: MemberManagementTools, team_settings: Settings, tmp_path: Path
):
    """Writes .md file to MEMBERS_DIR."""
    with (
        patch.object(Settings, "save", return_value=None),
        patch("vandelay.tools.member_management.MEMBERS_DIR", tmp_path),
    ):
        result = toolkit.add_team_member(
            "writer", "Content writer", "", "# Writer\nFocus on blog posts."
        )

    assert "added" in result.lower()
    md_file = tmp_path / "writer.md"
    assert md_file.exists()
    assert "blog posts" in md_file.read_text(encoding="utf-8")


def test_add_duplicate_name(toolkit: MemberManagementTools):
    """Duplicate name returns error."""
    result = toolkit.add_team_member("cto", "Another CTO")
    assert "already exists" in result.lower()


def test_add_invalid_name(toolkit: MemberManagementTools):
    """Invalid name returns error."""
    result = toolkit.add_team_member("123bad", "Bad name")
    assert "Invalid name" in result

    result2 = toolkit.add_team_member("has spaces", "Bad name")
    assert "Invalid name" in result2


def test_add_unenabled_tool_warns(
    toolkit: MemberManagementTools, team_settings: Settings
):
    """Warns about unenabled tools but still adds the member."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.add_team_member("newbie", "Newcomer", "shell,docker")

    assert "Warning" in result
    assert "docker" in result
    # Member still added
    names = [m.name for m in team_settings.team.members if isinstance(m, MemberConfig)]
    assert "newbie" in names


# --- update_member_config ---


def test_update_config_role(
    toolkit: MemberManagementTools, team_settings: Settings
):
    """Changes role."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.update_member_config("cto", role="VP of Engineering")

    assert "updated" in result.lower()
    mc = next(m for m in team_settings.team.members if isinstance(m, MemberConfig) and m.name == "cto")
    assert mc.role == "VP of Engineering"


def test_update_config_tools(
    toolkit: MemberManagementTools, team_settings: Settings
):
    """Replaces tool list."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.update_member_config("cto", tools="shell,file,tavily")

    assert "updated" in result.lower()
    mc = next(m for m in team_settings.team.members if isinstance(m, MemberConfig) and m.name == "cto")
    assert mc.tools == ["shell", "file", "tavily"]


def test_update_config_nothing(toolkit: MemberManagementTools):
    """Empty role and tools returns nothing-to-update message."""
    result = toolkit.update_member_config("cto")
    assert "Nothing to update" in result


def test_update_config_unknown_member(toolkit: MemberManagementTools):
    """Unknown member returns error with available names."""
    result = toolkit.update_member_config("ghost", role="Phantom")
    assert "Unknown member" in result


# --- update_member_instructions ---


def test_update_instructions(
    toolkit: MemberManagementTools, team_settings: Settings, tmp_path: Path
):
    """Writes file and sets instructions_file."""
    with (
        patch.object(Settings, "save", return_value=None),
        patch("vandelay.tools.member_management.MEMBERS_DIR", tmp_path),
    ):
        result = toolkit.update_member_instructions("cto", "# CTO\nFocus on architecture.")

    assert "saved" in result.lower()
    md_file = tmp_path / "cto.md"
    assert md_file.exists()
    assert "architecture" in md_file.read_text(encoding="utf-8")

    mc = next(m for m in team_settings.team.members if isinstance(m, MemberConfig) and m.name == "cto")
    assert mc.instructions_file == "cto.md"


def test_update_instructions_empty(toolkit: MemberManagementTools):
    """Empty instructions returns error."""
    result = toolkit.update_member_instructions("cto", "   ")
    assert "cannot be empty" in result.lower()


def test_update_instructions_unknown_member(toolkit: MemberManagementTools):
    """Unknown member returns error."""
    result = toolkit.update_member_instructions("ghost", "# Ghost")
    assert "Unknown member" in result


# --- remove_team_member ---


def test_remove_member(
    toolkit: MemberManagementTools, team_settings: Settings, reload_tracker: dict
):
    """Removes from list, file untouched."""
    with patch.object(Settings, "save", return_value=None):
        result = toolkit.remove_team_member("research")

    assert "removed" in result.lower()
    names = [m if isinstance(m, str) else m.name for m in team_settings.team.members]
    assert "research" not in names
    assert reload_tracker["count"] == 1


def test_remove_nonexistent(toolkit: MemberManagementTools):
    """Removing nonexistent member returns error."""
    result = toolkit.remove_team_member("ghost")
    assert "Unknown member" in result


# --- reload callback ---


def test_reload_called(
    toolkit: MemberManagementTools, team_settings: Settings, reload_tracker: dict
):
    """Verifies reload_callback fires on mutations."""
    with patch.object(Settings, "save", return_value=None):
        toolkit.add_team_member("temp", "Temporary")
        assert reload_tracker["count"] == 1

        toolkit.update_member_config("temp", role="Updated")
        assert reload_tracker["count"] == 2

        toolkit.remove_team_member("temp")
        assert reload_tracker["count"] == 3
