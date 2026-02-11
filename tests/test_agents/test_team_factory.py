"""Tests for team factory — create_team() and backward compatibility."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from vandelay.config.models import KnowledgeConfig, ModelConfig, TeamConfig
from vandelay.config.settings import Settings


class TestCreateTeam:
    def _make_settings(self, **overrides) -> Settings:
        defaults = dict(
            agent_name="TestTeam",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=True),
        )
        defaults.update(overrides)
        return Settings(**defaults)

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_system_prompt")
    def test_create_team_builds_team(
        self,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_team_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=["browser", "system"]),
            workspace_dir=str(tmp_path),
        )

        mock_browser = MagicMock(return_value=MagicMock())
        mock_system = MagicMock(return_value=MagicMock())
        with patch(
            "vandelay.agents.specialists.agents.SPECIALIST_FACTORIES",
            {"browser": mock_browser, "system": mock_system},
        ):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert call_kwargs["id"] == "vandelay-team"
        assert call_kwargs["name"] == "TestTeam"
        assert call_kwargs["respond_directly"] is True
        assert len(call_kwargs["members"]) == 2

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_system_prompt")
    def test_create_team_skips_unknown_members(
        self,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_team_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=["unknown_specialist"]),
            workspace_dir=str(tmp_path),
        )

        with patch(
            "vandelay.agents.specialists.agents.SPECIALIST_FACTORIES", {},
        ):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert len(call_kwargs["members"]) == 0

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_system_prompt")
    def test_create_team_includes_tool_management(
        self,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_team_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=[]),
            workspace_dir=str(tmp_path),
        )

        with patch(
            "vandelay.agents.specialists.agents.SPECIALIST_FACTORIES", {},
        ):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert len(call_kwargs["tools"]) == 1


class TestBackwardCompatibility:
    """Ensure create_agent still works independently of team mode."""

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("vandelay.agents.factory.Agent")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory._get_tools")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_system_prompt")
    def test_create_agent_still_works(
        self,
        mock_prompt,
        mock_db,
        mock_tools,
        mock_model,
        mock_agent_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_agent

        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_tools.return_value = []
        mock_agent_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = Settings(
            agent_name="TestAgent",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=False),
            workspace_dir=str(tmp_path),
        )

        create_agent(settings)

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["id"] == "vandelay-main"

    def test_settings_defaults_team_disabled(self):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
        )
        assert settings.team.enabled is False

    def test_settings_team_enabled(self):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=True),
        )
        assert settings.team.enabled is True
