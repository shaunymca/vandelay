"""Backward-compatibility tests — legacy string member names still produce valid agents."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from vandelay.agents.factory import _resolve_member
from vandelay.config.models import MemberConfig, ModelConfig
from vandelay.config.settings import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        agent_name="Test",
        model=ModelConfig(provider="ollama"),
        workspace_dir=".",
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestLegacyMemberNames:
    """Ensure legacy string member names resolve correctly through the new factory."""

    def test_all_legacy_names_resolve(self):
        for name in ("browser", "system", "scheduler", "knowledge"):
            mc = _resolve_member(name)
            assert isinstance(mc, MemberConfig)
            assert mc.name == name

    @patch("vandelay.agents.factory.Agent")
    def test_legacy_browser_creates_agent(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = _resolve_member("browser")
        settings = _make_settings(enabled_tools=["crawl4ai"])

        with patch("vandelay.tools.manager.ToolManager") as mock_mgr:
            mock_mgr.return_value.instantiate_tools.return_value = [MagicMock()]
            _build_member_agent(
                mc,
                main_model=MagicMock(),
                db=MagicMock(),
                knowledge=None,
                settings=settings,
                personality_brief="",
            )

        kwargs = mock_agent.call_args[1]
        assert kwargs["id"] == "vandelay-browser"
        assert kwargs["role"] is not None

    @patch("vandelay.agents.factory.Agent")
    def test_legacy_system_creates_agent(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = _resolve_member("system")
        settings = _make_settings(enabled_tools=["shell", "file"])

        with patch("vandelay.tools.manager.ToolManager") as mock_mgr:
            mock_mgr.return_value.instantiate_tools.return_value = [MagicMock()]
            _build_member_agent(
                mc,
                main_model=MagicMock(),
                db=MagicMock(),
                knowledge=None,
                settings=settings,
                personality_brief="",
            )

        kwargs = mock_agent.call_args[1]
        assert kwargs["id"] == "vandelay-system"

    @patch("vandelay.agents.factory.Agent")
    def test_legacy_knowledge_creates_agent(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = _resolve_member("knowledge")
        mock_knowledge = MagicMock()
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=MagicMock(),
            db=MagicMock(),
            knowledge=mock_knowledge,
            settings=settings,
            personality_brief="",
        )

        kwargs = mock_agent.call_args[1]
        assert kwargs["id"] == "vandelay-knowledge"
        assert kwargs["knowledge"] is mock_knowledge
        assert kwargs["search_knowledge"] is True
