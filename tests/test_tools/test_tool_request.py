"""Tests for the ToolRequestTools member toolkit."""

from __future__ import annotations

from pathlib import Path

import pytest

from vandelay.config.models import MemberConfig, ModelConfig, TeamConfig
from vandelay.config.settings import Settings
from vandelay.tools.tool_request import ToolRequestTools


@pytest.fixture
def team_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestTeam",
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
def cto_toolkit(team_settings: Settings) -> ToolRequestTools:
    return ToolRequestTools(settings=team_settings, member_name="cto")


class TestToolRequestTools:
    def test_request_enabled_not_assigned(self, cto_toolkit):
        """Tool is globally enabled but member doesn't have it."""
        result = cto_toolkit.request_tool("tavily", "Need to search the web")
        assert "TOOL_REQUEST:" in result
        assert "status=enabled_not_assigned" in result
        assert "tool=tavily" in result

    def test_request_not_enabled(self, cto_toolkit):
        """Tool exists in registry but isn't globally enabled."""
        result = cto_toolkit.request_tool("duckduckgo", "Need web search")
        assert "status=not_enabled" in result
        assert "tool=duckduckgo" in result

    def test_request_not_found(self, cto_toolkit):
        """Tool doesn't exist in the registry at all."""
        result = cto_toolkit.request_tool(
            "baseball_stats", "Need MLB player statistics",
        )
        assert "status=not_found" in result
        assert "tool=baseball_stats" in result

    def test_request_includes_member_name(self, cto_toolkit):
        """Response should include the requesting member's name."""
        result = cto_toolkit.request_tool("tavily", "Need search")
        assert "requesting_member=cto" in result

    def test_request_includes_reason(self, cto_toolkit):
        """Response should include the reason for the request."""
        result = cto_toolkit.request_tool(
            "gmail", "Need to send a follow-up email",
        )
        assert "reason=Need to send a follow-up email" in result
