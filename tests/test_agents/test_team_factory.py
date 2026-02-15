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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_create_team_builds_team(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_team_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=["browser", "system"]),
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_user_id_passed_to_team(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        """Bug fix: user_id must be passed to Team constructor."""
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_user_id_defaults_when_empty(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_mode_comes_from_config(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_route_mode_respond_directly(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_mixed_string_and_memberconfig_members(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_personality_brief_injected(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = "Be helpful and direct."
        mock_prompt.return_value = ["test"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_team_cls.return_value = MagicMock()
        mock_create_knowledge.return_value = None

        settings = self._make_settings(
            team=TeamConfig(enabled=True, members=["browser"]),
            workspace_dir=str(tmp_path),
        )

        with patch("vandelay.agents.factory.Agent") as mock_agent:
            mock_agent.return_value = MagicMock()
            create_team(settings)

        # The Agent was called once for the browser member
        agent_kwargs = mock_agent.call_args[1]
        assert "Be helpful and direct." in agent_kwargs["instructions"]

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("agno.team.Team")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_team_leader_prompt")
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_includes_tool_management(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
        assert len(call_kwargs["tools"]) == 2  # ToolManagementTools + WorkspaceTools


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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_member_gets_scoped_user_id(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_member_has_memory_enabled(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_leader_keeps_global_user_id(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
    @patch("vandelay.agents.factory.build_personality_brief")
    def test_each_member_gets_unique_scope(
        self,
        mock_brief,
        mock_prompt,
        mock_db,
        mock_model,
        mock_team_cls,
        mock_create_knowledge,
        tmp_path,
    ):
        from vandelay.agents.factory import create_team

        mock_brief.return_value = ""
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
