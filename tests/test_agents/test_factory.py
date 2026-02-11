"""Tests for agent factory — model creation and knowledge wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import KnowledgeConfig, ModelConfig
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
