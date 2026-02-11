"""Tests for specialist agent factories."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from vandelay.agents.specialists.agents import (
    SPECIALIST_FACTORIES,
    create_browser_agent,
    create_knowledge_agent,
    create_scheduler_agent,
    create_system_agent,
)
from vandelay.config.models import ModelConfig
from vandelay.config.settings import Settings

# Patch target for Agent class (imported at module level in specialists)
_AGENT_CLS = "vandelay.agents.specialists.agents.Agent"
# ToolManager and SchedulerTools are local imports — patch at source
_TOOL_MGR = "vandelay.tools.manager.ToolManager"
_SCHED_TOOLS = "vandelay.tools.scheduler.SchedulerTools"


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        agent_name="Test",
        model=ModelConfig(provider="ollama"),
        workspace_dir=".",
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestSpecialistFactories:
    def test_registry_has_all_specialists(self):
        assert set(SPECIALIST_FACTORIES.keys()) == {
            "browser", "system", "scheduler", "knowledge",
        }

    @patch(_TOOL_MGR)
    @patch(_AGENT_CLS)
    def test_browser_agent_id(self, mock_agent_cls, mock_mgr):
        mock_mgr.return_value.instantiate_tools.return_value = [MagicMock()]
        settings = _make_settings(enabled_tools=["crawl4ai"])
        mock_agent_cls.return_value = MagicMock()

        create_browser_agent(
            model=MagicMock(), db=MagicMock(), knowledge=None, settings=settings,
        )

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["id"] == "vandelay-browser"
        assert call_kwargs["role"] is not None

    @patch(_TOOL_MGR)
    @patch(_AGENT_CLS)
    def test_system_agent_filters_tools(self, mock_agent_cls, mock_mgr):
        mock_mgr.return_value.instantiate_tools.return_value = [MagicMock()]
        settings = _make_settings(enabled_tools=["shell", "file", "crawl4ai"])
        mock_agent_cls.return_value = MagicMock()

        create_system_agent(
            model=MagicMock(), db=MagicMock(), knowledge=None, settings=settings,
        )

        # Should only instantiate shell and file, not crawl4ai
        instantiate_call = mock_mgr.return_value.instantiate_tools
        tool_names = instantiate_call.call_args[0][0]
        assert "shell" in tool_names
        assert "file" in tool_names
        assert "crawl4ai" not in tool_names

    @patch(_SCHED_TOOLS)
    @patch(_AGENT_CLS)
    def test_scheduler_agent_with_engine(self, mock_agent_cls, mock_sched_cls):
        mock_agent_cls.return_value = MagicMock()
        mock_sched_cls.return_value = MagicMock()
        mock_engine = MagicMock()
        settings = _make_settings()

        create_scheduler_agent(
            model=MagicMock(), db=MagicMock(), knowledge=None,
            settings=settings, scheduler_engine=mock_engine,
        )

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["id"] == "vandelay-scheduler"
        assert call_kwargs["tools"] is not None

    @patch(_AGENT_CLS)
    def test_scheduler_agent_without_engine(self, mock_agent_cls):
        mock_agent_cls.return_value = MagicMock()
        settings = _make_settings()

        create_scheduler_agent(
            model=MagicMock(), db=MagicMock(), knowledge=None,
            settings=settings, scheduler_engine=None,
        )

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["tools"] is None

    @patch(_AGENT_CLS)
    def test_knowledge_agent_with_knowledge(self, mock_agent_cls):
        mock_agent_cls.return_value = MagicMock()
        mock_knowledge = MagicMock()
        settings = _make_settings()

        create_knowledge_agent(
            model=MagicMock(), db=MagicMock(), knowledge=mock_knowledge,
            settings=settings,
        )

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["id"] == "vandelay-knowledge"
        assert call_kwargs["knowledge"] is mock_knowledge
        assert call_kwargs["search_knowledge"] is True

    @patch(_AGENT_CLS)
    def test_knowledge_agent_without_knowledge(self, mock_agent_cls):
        mock_agent_cls.return_value = MagicMock()
        settings = _make_settings()

        create_knowledge_agent(
            model=MagicMock(), db=MagicMock(), knowledge=None,
            settings=settings,
        )

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["search_knowledge"] is False

    @patch(_AGENT_CLS)
    def test_browser_agent_no_browser_tools(self, mock_agent_cls):
        """Browser agent with no browser tools enabled should have tools=None."""
        mock_agent_cls.return_value = MagicMock()
        settings = _make_settings(enabled_tools=["shell"])

        create_browser_agent(
            model=MagicMock(), db=MagicMock(), knowledge=None, settings=settings,
        )

        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["tools"] is None
