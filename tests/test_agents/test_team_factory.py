"""Tests for team factory — create_team() with configurable members."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from vandelay.config.models import KnowledgeConfig, MemberConfig, ModelConfig, TeamConfig
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
    @patch("vandelay.agents.factory.build_team_leader_prompt")
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
            team=TeamConfig(
                enabled=True,
                members=[
                    MemberConfig(name="researcher", tools=[]),
                    MemberConfig(name="coder", tools=[]),
                ],
            ),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent"):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert call_kwargs["id"] == "vandelay-team"
        assert call_kwargs["name"] == "TestTeam"
        assert len(call_kwargs["members"]) == 2

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_user_id_passed_to_team(
        self,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        """Bug fix: user_id must be passed to Team constructor."""
        from vandelay.agents.factory import create_team

        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_team_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = self._make_settings(
            user_id="test@example.com",
            team=TeamConfig(enabled=True, members=[]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent"):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert call_kwargs["user_id"] == "test@example.com"

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_user_id_defaults_when_empty(
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

        with patch("vandelay.agents.factory.Agent"):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert call_kwargs["user_id"] == "default"

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_mode_comes_from_config(
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
            team=TeamConfig(enabled=True, mode="coordinate", members=[]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent"):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert call_kwargs["mode"] == "coordinate"
        assert call_kwargs["respond_directly"] is False

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_route_mode_respond_directly(
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
            team=TeamConfig(enabled=True, mode="route", members=[]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent"):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert call_kwargs["mode"] == "route"
        assert call_kwargs["respond_directly"] is True

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_mixed_string_and_memberconfig_members(
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

        mc = MemberConfig(name="cto", tools=["shell"])
        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=["browser", mc]),
            enabled_tools=["shell", "crawl4ai"],
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent") as mock_agent:
            mock_agent.return_value = MagicMock()
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        assert len(call_kwargs["members"]) == 2

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_includes_tool_management(
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

        with patch("vandelay.agents.factory.Agent"):
            create_team(settings)

        call_kwargs = mock_team_cls.call_args[1]
        # The leader now receives management tools + any user-enabled tools.
        # With no enabled_tools in this test, we get at least the 3 management toolkits.
        tool_type_names = [type(t).__name__ for t in call_kwargs["tools"]]
        assert "ToolManagementTools" in tool_type_names
        assert "WorkspaceTools" in tool_type_names
        assert "MemberManagementTools" in tool_type_names


class TestMemberMemoryScoping:
    """Members get scoped user_id and memory; leader keeps global user_id."""

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
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_member_gets_scoped_user_id(
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

        mc = MemberConfig(name="personal-assistant", role="PA")
        settings = self._make_settings(
            user_id="shaun@agno.com",
            team=TeamConfig(enabled=True, members=[mc]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent") as mock_agent:
            mock_agent.return_value = MagicMock()
            create_team(settings)

        agent_kwargs = mock_agent.call_args[1]
        assert agent_kwargs["user_id"] == "member_personal-assistant"

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_member_has_memory_enabled(
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

        mc = MemberConfig(name="cto", role="CTO")
        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=[mc]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent") as mock_agent:
            mock_agent.return_value = MagicMock()
            create_team(settings)

        agent_kwargs = mock_agent.call_args[1]
        assert agent_kwargs["update_memory_on_run"] is True

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_leader_keeps_global_user_id(
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

        mc = MemberConfig(name="pa", role="PA")
        settings = self._make_settings(
            user_id="shaun@agno.com",
            team=TeamConfig(enabled=True, members=[mc]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent") as mock_agent:
            mock_agent.return_value = MagicMock()
            create_team(settings)

        team_kwargs = mock_team_cls.call_args[1]
        assert team_kwargs["user_id"] == "shaun@agno.com"

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    def test_each_member_gets_unique_scope(
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
            team=TeamConfig(
                enabled=True,
                members=[
                    MemberConfig(name="cto", role="CTO"),
                    MemberConfig(name="pa", role="PA"),
                ],
            ),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent") as mock_agent:
            mock_agent.return_value = MagicMock()
            create_team(settings)

        # Agent called twice — once per member
        calls = mock_agent.call_args_list
        user_ids = {c[1]["user_id"] for c in calls}
        assert user_ids == {"member_cto", "member_pa"}


class TestBackwardCompatibility:
    """Ensure create_agent still works independently of team mode."""

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("vandelay.agents.factory.Agent")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory._get_tools")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
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

    def test_settings_defaults_team_enabled(self):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
        )
        assert settings.team.enabled is True
        assert settings.team.members == ["vandelay-expert"]

    def test_settings_team_disabled_override(self):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=False, members=[]),
        )
        assert settings.team.enabled is False
