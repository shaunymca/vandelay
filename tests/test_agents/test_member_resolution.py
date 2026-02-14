"""Tests for _resolve_member, _build_member_agent, and _load_instructions_file."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import MemberConfig, ModelConfig, TeamConfig
from vandelay.config.settings import Settings


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        agent_name="Test",
        model=ModelConfig(provider="ollama"),
        workspace_dir=".",
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestResolveember:
    def test_string_browser(self):
        from vandelay.agents.factory import _resolve_member

        mc = _resolve_member("browser")
        assert isinstance(mc, MemberConfig)
        assert mc.name == "browser"
        assert mc.tools == ["crawl4ai", "camofox"]
        assert mc.role == "Web browsing, scraping, and screenshot specialist"

    def test_string_system(self):
        from vandelay.agents.factory import _resolve_member

        mc = _resolve_member("system")
        assert mc.name == "system"
        assert mc.tools == ["shell", "file", "python"]

    def test_string_scheduler(self):
        from vandelay.agents.factory import _resolve_member

        mc = _resolve_member("scheduler")
        assert mc.name == "scheduler"
        assert mc.tools == []  # SchedulerTools injected separately

    def test_string_knowledge(self):
        from vandelay.agents.factory import _resolve_member

        mc = _resolve_member("knowledge")
        assert mc.name == "knowledge"
        assert mc.tools == []

    def test_unknown_string_gets_empty_tools(self):
        from vandelay.agents.factory import _resolve_member

        mc = _resolve_member("unknown_thing")
        assert mc.name == "unknown_thing"
        assert mc.tools == []
        assert mc.role == ""

    def test_memberconfig_passthrough(self):
        from vandelay.agents.factory import _resolve_member

        original = MemberConfig(
            name="cto", tools=["shell"], role="Lead Dev",
        )
        result = _resolve_member(original)
        assert result is original


class TestBuildMemberAgent:
    @patch("vandelay.agents.factory.Agent")
    def test_creates_agent_with_correct_params(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = MemberConfig(name="test", role="Test role")
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=MagicMock(),
            db=MagicMock(),
            knowledge=None,
            settings=settings,
            personality_brief="",
        )

        kwargs = mock_agent.call_args[1]
        assert kwargs["id"] == "vandelay-test"
        assert kwargs["name"] == "Test Specialist"
        assert kwargs["role"] == "Test role"

    @patch("vandelay.agents.factory._get_model_from_config")
    @patch("vandelay.agents.factory.Agent")
    def test_per_member_model_override(self, mock_agent, mock_model_factory):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        custom_model = MagicMock()
        mock_model_factory.return_value = custom_model
        main_model = MagicMock()

        mc = MemberConfig(
            name="cto",
            model_provider="openai",
            model_id="gpt-4o",
        )
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=main_model,
            db=MagicMock(),
            knowledge=None,
            settings=settings,
            personality_brief="",
        )

        mock_model_factory.assert_called_once_with("openai", "gpt-4o")
        kwargs = mock_agent.call_args[1]
        assert kwargs["model"] is custom_model

    @patch("vandelay.agents.factory.Agent")
    def test_inherits_main_model_when_no_override(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        main_model = MagicMock()

        mc = MemberConfig(name="test")
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=main_model,
            db=MagicMock(),
            knowledge=None,
            settings=settings,
            personality_brief="",
        )

        kwargs = mock_agent.call_args[1]
        assert kwargs["model"] is main_model

    @patch("vandelay.agents.factory.Agent")
    def test_personality_brief_in_instructions(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = MemberConfig(name="test")
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=MagicMock(),
            db=MagicMock(),
            knowledge=None,
            settings=settings,
            personality_brief="Be direct and helpful.",
        )

        kwargs = mock_agent.call_args[1]
        assert "Be direct and helpful." in kwargs["instructions"]

    @patch("vandelay.agents.factory.Agent")
    def test_inline_instructions_appended(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = MemberConfig(name="test", instructions=["Focus on code quality"])
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=MagicMock(),
            db=MagicMock(),
            knowledge=None,
            settings=settings,
            personality_brief="Brief.",
        )

        kwargs = mock_agent.call_args[1]
        assert "Brief." in kwargs["instructions"]
        assert "Focus on code quality" in kwargs["instructions"]

    @patch("vandelay.agents.factory.Agent")
    def test_tools_intersected_with_enabled(self, mock_agent):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        mc = MemberConfig(name="test", tools=["shell", "file", "tavily"])
        # Only shell is enabled — file and tavily should be filtered out
        settings = _make_settings(enabled_tools=["shell"])

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
            tool_names = mock_mgr.return_value.instantiate_tools.call_args[0][0]
            assert tool_names == ["shell"]


class TestLoadInstructionsFile:
    def test_loads_from_file(self, tmp_path):
        from vandelay.agents.factory import _load_instructions_file

        instructions_file = tmp_path / "test.md"
        instructions_file.write_text("Be a great CTO.", encoding="utf-8")

        with patch("vandelay.config.constants.MEMBERS_DIR", tmp_path):
            result = _load_instructions_file("test.md")

        assert result == "Be a great CTO."

    def test_missing_file_logs_warning(self, tmp_path, caplog):
        from vandelay.agents.factory import _load_instructions_file

        with patch("vandelay.config.constants.MEMBERS_DIR", tmp_path):
            with caplog.at_level(logging.WARNING):
                result = _load_instructions_file("nonexistent.md")

        assert result == ""
        assert "not found" in caplog.text

    def test_empty_path_returns_empty(self):
        from vandelay.agents.factory import _load_instructions_file

        assert _load_instructions_file("") == ""

    def test_absolute_path(self, tmp_path):
        from vandelay.agents.factory import _load_instructions_file

        instructions_file = tmp_path / "absolute_test.md"
        instructions_file.write_text("Absolute instructions.", encoding="utf-8")

        result = _load_instructions_file(str(instructions_file))
        assert result == "Absolute instructions."

    @patch("vandelay.agents.factory.Agent")
    def test_file_merged_with_inline_instructions(self, mock_agent, tmp_path):
        from vandelay.agents.factory import _build_member_agent

        mock_agent.return_value = MagicMock()
        instructions_file = tmp_path / "cto.md"
        instructions_file.write_text("File instructions here.", encoding="utf-8")

        mc = MemberConfig(
            name="cto",
            instructions=["Inline instruction."],
            instructions_file=str(instructions_file),
        )
        settings = _make_settings()

        _build_member_agent(
            mc,
            main_model=MagicMock(),
            db=MagicMock(),
            knowledge=None,
            settings=settings,
            personality_brief="Brief.",
        )

        kwargs = mock_agent.call_args[1]
        instructions = kwargs["instructions"]
        # Order: tag, personality brief, file, inline
        assert "[CTO]" in instructions[0]
        assert instructions[1] == "Brief."
        assert instructions[2] == "File instructions here."
        assert instructions[3] == "Inline instruction."
