"""Tests for agent factory — model creation, knowledge wiring, and team defaults."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import KnowledgeConfig, MemberConfig, ModelConfig, TeamConfig
from vandelay.config.settings import Settings


class TestGetModel:
    """Test _get_model for various providers."""

    def _make_settings(self, provider: str, model_id: str = "test-model") -> Settings:
        return Settings(
            agent_name="Test",
            model=ModelConfig(provider=provider, model_id=model_id),
        )

    def test_openrouter_uses_openai_chat(self):
        from vandelay.agents.factory import _get_model

        mock_cls = MagicMock(return_value=MagicMock())
        settings = self._make_settings("openrouter", "anthropic/claude-sonnet-4-5-20250929")

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "or-test-key"}):
            with patch.dict(
                "sys.modules",
                {"agno.models.openai": MagicMock(OpenAIChat=mock_cls)},
            ):
                result = _get_model(settings)
                mock_cls.assert_called_once_with(
                    id="anthropic/claude-sonnet-4-5-20250929",
                    api_key="or-test-key",
                    base_url="https://openrouter.ai/api/v1",
                )

    def test_unknown_provider_raises(self):
        from vandelay.agents.factory import _get_model

        settings = self._make_settings("totally_unknown")
        with pytest.raises(ValueError, match="Unknown model provider"):
            _get_model(settings)


class TestKnowledgeWiring:
    """Test that knowledge is wired into create_agent."""

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("vandelay.agents.factory.Agent")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory._get_tools")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_system_prompt")
    def test_knowledge_passed_to_agent(
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

        mock_knowledge = MagicMock()
        mock_create_knowledge.return_value = mock_knowledge
        mock_prompt.return_value = ["test instruction"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_tools.return_value = []
        mock_agent_cls.return_value = MagicMock()

        settings = Settings(
            agent_name="TestAgent",
            model=ModelConfig(provider="ollama"),
            knowledge=KnowledgeConfig(enabled=True),
            workspace_dir=str(tmp_path),
        )

        create_agent(settings)

        # Verify knowledge was passed to Agent constructor
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["knowledge"] is mock_knowledge
        assert call_kwargs["search_knowledge"] is True

    @patch("vandelay.knowledge.setup.create_knowledge")
    @patch("vandelay.agents.factory.Agent")
    @patch("vandelay.agents.factory._get_model")
    @patch("vandelay.agents.factory._get_tools")
    @patch("vandelay.agents.factory.create_db")
    @patch("vandelay.agents.factory.build_system_prompt")
    def test_knowledge_none_when_disabled(
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

        mock_create_knowledge.return_value = None
        mock_prompt.return_value = ["test instruction"]
        mock_db.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_tools.return_value = []
        mock_agent_cls.return_value = MagicMock()

        settings = Settings(
            agent_name="TestAgent",
            model=ModelConfig(provider="ollama"),
            knowledge=KnowledgeConfig(enabled=False),
            workspace_dir=str(tmp_path),
        )

        create_agent(settings)

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["knowledge"] is None
        assert call_kwargs["search_knowledge"] is False


class TestTeamConfigDefaults:
    """Verify TeamConfig ships with team mode on and vandelay-expert."""

    def test_team_enabled_by_default(self):
        tc = TeamConfig()
        assert tc.enabled is True

    def test_team_default_members(self):
        tc = TeamConfig()
        assert tc.members == ["vandelay-expert"]

    def test_team_disabled_override(self):
        tc = TeamConfig(enabled=False, members=[])
        assert tc.enabled is False
        assert tc.members == []


class TestResolveMember:
    """Test _resolve_member and _ensure_template_instructions."""

    def test_resolve_member_vandelay_expert(self, tmp_path):
        from vandelay.agents.factory import _resolve_member

        with patch("vandelay.config.constants.MEMBERS_DIR", tmp_path / "members"):
            mc = _resolve_member("vandelay-expert")

        assert isinstance(mc, MemberConfig)
        assert mc.name == "vandelay-expert"
        assert mc.role == (
            "Agent builder — designs, creates, tests, and improves team member agents"
        )
        assert mc.tools == ["file", "python", "shell"]
        assert mc.instructions_file == "vandelay-expert.md"

    def test_resolve_member_config_passthrough(self):
        from vandelay.agents.factory import _resolve_member

        original = MemberConfig(name="custom", role="test")
        result = _resolve_member(original)
        assert result is original

    def test_ensure_template_creates_file(self, tmp_path):
        from vandelay.agents.factory import _ensure_template_instructions

        members_dir = tmp_path / "members"
        mc = MemberConfig(name="vandelay-expert", role="test", tools=["file"])

        with patch("vandelay.config.constants.MEMBERS_DIR", members_dir):
            result = _ensure_template_instructions(mc)

        assert result.instructions_file == "vandelay-expert.md"
        assert (members_dir / "vandelay-expert.md").exists()
        content = (members_dir / "vandelay-expert.md").read_text(encoding="utf-8")
        assert len(content) > 0

    def test_ensure_template_skips_existing(self, tmp_path):
        from vandelay.agents.factory import _ensure_template_instructions

        members_dir = tmp_path / "members"
        members_dir.mkdir()
        existing = members_dir / "vandelay-expert.md"
        existing.write_text("custom content", encoding="utf-8")

        mc = MemberConfig(name="vandelay-expert", role="test", tools=["file"])

        with patch("vandelay.config.constants.MEMBERS_DIR", members_dir):
            result = _ensure_template_instructions(mc)

        assert result.instructions_file == "vandelay-expert.md"
        # Should NOT have overwritten
        assert existing.read_text(encoding="utf-8") == "custom content"

    def test_ensure_template_no_template(self):
        from vandelay.agents.factory import _ensure_template_instructions

        mc = MemberConfig(name="unknown-agent", role="test")
        result = _ensure_template_instructions(mc)
        assert result.instructions_file == ""

    def test_ensure_template_skips_if_instructions_file_set(self):
        from vandelay.agents.factory import _ensure_template_instructions

        mc = MemberConfig(
            name="vandelay-expert",
            role="test",
            instructions_file="custom.md",
        )
        result = _ensure_template_instructions(mc)
        assert result.instructions_file == "custom.md"
