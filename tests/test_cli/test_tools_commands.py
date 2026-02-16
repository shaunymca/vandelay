"""Tests for CLI tool commands — member assignment on enable."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from vandelay.cli.tools_commands import _prompt_member_assignment
from vandelay.config.models import MemberConfig, ModelConfig, TeamConfig
from vandelay.config.settings import Settings


@pytest.fixture
def team_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
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
def solo_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=["shell"],
        team=TeamConfig(enabled=False),
        db_url="",
    )


class TestPromptMemberAssignment:
    def test_skips_when_team_disabled(self, solo_settings):
        """Should return immediately when team mode is off."""
        # If it tried to show a questionary prompt, it would hang — passing = success
        _prompt_member_assignment("shell", solo_settings)

    def test_skips_when_no_members(self, tmp_path):
        """Should return immediately when team has no members."""
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=True, members=[]),
            workspace_dir=str(tmp_path),
        )
        _prompt_member_assignment("shell", settings)

    def test_assigns_selected_members(self, team_settings):
        """Should add tool to selected members and save."""
        with (
            patch("vandelay.cli.tools_commands.questionary") as mock_q,
            patch.object(Settings, "save", return_value=None) as mock_save,
        ):
            mock_q.checkbox.return_value.ask.return_value = ["cto"]
            _prompt_member_assignment("file", team_settings)

        # cto should now have "file" in tools
        cto = team_settings.team.members[0]
        assert "file" in cto.tools
        mock_save.assert_called_once()

    def test_no_selection_skips_save(self, team_settings):
        """Should not save when user selects nothing."""
        with (
            patch("vandelay.cli.tools_commands.questionary") as mock_q,
            patch.object(Settings, "save", return_value=None) as mock_save,
        ):
            mock_q.checkbox.return_value.ask.return_value = []
            _prompt_member_assignment("file", team_settings)

        mock_save.assert_not_called()

    def test_does_not_duplicate_existing_tool(self, team_settings):
        """Should not add tool if member already has it."""
        with (
            patch("vandelay.cli.tools_commands.questionary") as mock_q,
            patch.object(Settings, "save", return_value=None),
        ):
            # cto already has "shell"
            mock_q.checkbox.return_value.ask.return_value = ["cto"]
            _prompt_member_assignment("shell", team_settings)

        cto = team_settings.team.members[0]
        assert cto.tools.count("shell") == 1

    def test_assigns_to_multiple_members(self, team_settings):
        """Should assign tool to all selected members."""
        with (
            patch("vandelay.cli.tools_commands.questionary") as mock_q,
            patch.object(Settings, "save", return_value=None),
        ):
            mock_q.checkbox.return_value.ask.return_value = ["cto", "research"]
            _prompt_member_assignment("file", team_settings)

        cto = team_settings.team.members[0]
        research = team_settings.team.members[1]
        assert "file" in cto.tools
        assert "file" in research.tools
