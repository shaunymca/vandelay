"""Tests for system prompt builder."""

from pathlib import Path

import pytest

from vandelay.agents.prompts.system_prompt import (
    build_system_prompt,
    build_team_leader_prompt,
    _build_agents_slim,
    _build_credentials_summary,
    _build_deep_work_prompt,
    _build_member_roster,
)
from vandelay.config.models import (
    DeepWorkConfig,
    MemberConfig,
    ModelConfig,
    SafetyConfig,
    TeamConfig,
)
from vandelay.config.settings import Settings


@pytest.fixture
def prompt_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="tiered"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=["shell", "file"],
        db_url="",
    )


def test_build_prompt_includes_agent_name(tmp_workspace):
    """Prompt should include the agent's name."""
    prompt = build_system_prompt(agent_name="TestBot", workspace_dir=tmp_workspace)
    assert "TestBot" in prompt


def test_build_prompt_includes_current_datetime(tmp_workspace):
    """Prompt should include the current date so agents don't default to training cutoff."""
    from datetime import datetime

    prompt = build_system_prompt(agent_name="TestBot", workspace_dir=tmp_workspace)
    today = datetime.now().strftime("%B %d, %Y")
    assert "Current date and time:" in prompt
    assert today in prompt


def test_team_leader_prompt_includes_current_datetime(tmp_workspace, prompt_settings):
    """Team leader prompt should also include the current date."""
    from datetime import datetime

    prompt = build_team_leader_prompt(
        agent_name="TestBot",
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    today = datetime.now().strftime("%B %d, %Y")
    assert "Current date and time:" in prompt
    assert today in prompt


def test_build_prompt_includes_credentials_summary(tmp_workspace):
    """Prompt should include a credentials summary section."""
    prompt = build_system_prompt(agent_name="TestBot", workspace_dir=tmp_workspace)
    assert "Your Configured Credentials" in prompt
    assert "Do NOT ask the user to configure them" in prompt


def test_team_leader_prompt_includes_credentials_summary(tmp_workspace, prompt_settings):
    """Team leader prompt should also include credentials summary."""
    prompt = build_team_leader_prompt(
        agent_name="TestBot",
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    assert "Your Configured Credentials" in prompt


def test_build_prompt_includes_soul(tmp_workspace):
    """Prompt should include SOUL.md content."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Core Truths" in prompt
    assert "genuinely helpful" in prompt


def test_build_prompt_includes_user(tmp_workspace):
    """Prompt should include USER.md content."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Timezone" in prompt


def test_build_prompt_includes_agents(tmp_workspace):
    """Prompt should include AGENTS.md content."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Delegation" in prompt


def test_build_prompt_includes_tools(tmp_workspace):
    """Prompt should include TOOLS.md content."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Shell Commands" in prompt


def test_build_prompt_includes_memory(tmp_workspace):
    """Prompt should include MEMORY.md content."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Memory" in prompt


def test_build_prompt_includes_bootstrap(tmp_workspace):
    """Prompt should include BOOTSTRAP.md on first run."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Bootstrap" in prompt
    assert "Self-Destruct" in prompt


def test_build_prompt_excludes_bootstrap_after_removal(tmp_workspace):
    """Prompt should not include BOOTSTRAP.md after it's deleted."""
    bootstrap = tmp_workspace / "BOOTSTRAP.md"
    if bootstrap.exists():
        bootstrap.unlink()
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Self-Destruct" not in prompt


def test_build_prompt_includes_tool_catalog(tmp_workspace, prompt_settings):
    """Prompt should include the enabled tools section when settings provided."""
    prompt = build_system_prompt(
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    assert "Your Enabled Tools" in prompt
    assert "list_available_tools" in prompt


def test_build_prompt_catalog_shows_enabled(tmp_workspace, prompt_settings):
    """Tool catalog should list enabled tools."""
    prompt = build_system_prompt(
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    assert "**shell**" in prompt
    assert "**file**" in prompt


def test_build_prompt_catalog_shows_available(tmp_workspace, prompt_settings):
    """Tool catalog should not list non-enabled tools individually."""
    prompt = build_system_prompt(
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    # duckduckgo is a known tool that is NOT enabled — should not appear
    assert "**duckduckgo**" not in prompt


def test_build_prompt_no_catalog_without_settings(tmp_workspace):
    """Without settings, no tool catalog should appear."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Available Tool Catalog" not in prompt


# --- Team leader prompt tests ---


@pytest.fixture
def team_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestLeader",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        team=TeamConfig(
            enabled=True,
            members=[
                MemberConfig(name="cto", role="Technical architecture", tools=["shell", "file"]),
                MemberConfig(
                    name="research",
                    role="Web research",
                    tools=["tavily"],
                    model_provider="openai",
                    model_id="gpt-4o",
                ),
            ],
        ),
        enabled_tools=["shell", "file", "tavily"],
        workspace_dir=str(tmp_path / "workspace"),
        db_url="",
    )


class TestTeamLeaderPrompt:
    def test_leader_prompt_excludes_tools_md(self, tmp_workspace, team_settings):
        """Leader prompt should NOT include TOOLS.md content."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Shell Commands" not in prompt

    def test_leader_prompt_excludes_tool_catalog(self, tmp_workspace, team_settings):
        """Leader prompt should NOT include the tool catalog."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Your Enabled Tools" not in prompt

    def test_leader_prompt_includes_soul(self, tmp_workspace, team_settings):
        """Leader prompt should include SOUL.md."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Core Truths" in prompt

    def test_leader_prompt_includes_user(self, tmp_workspace, team_settings):
        """Leader prompt should include USER.md."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Timezone" in prompt

    def test_leader_prompt_includes_memory(self, tmp_workspace, team_settings):
        """Leader prompt should include MEMORY.md."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Memory" in prompt

    def test_leader_prompt_includes_roster(self, tmp_workspace, team_settings):
        """Leader prompt should include the member roster."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Your Team" in prompt
        assert "cto" in prompt
        assert "research" in prompt

    def test_leader_prompt_slim_agents(self, tmp_workspace, team_settings):
        """Leader prompt should include safety/style from AGENTS.md but not its Delegation section."""
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=team_settings,
        )
        assert "Safety Rules" in prompt
        assert "Response Style" in prompt
        # The AGENTS.md "## Delegation" section should be stripped (replaced by
        # the dynamic member roster which has its own "## Delegation Rules").
        assert "## Delegation\n" not in prompt

    def test_leader_prompt_includes_agent_name(self, tmp_workspace, team_settings):
        """Leader prompt should include the agent name."""
        prompt = build_team_leader_prompt(
            agent_name="LeaderBot",
            workspace_dir=tmp_workspace,
            settings=team_settings,
        )
        assert "LeaderBot" in prompt


class TestBuildAgentsSlim:
    def test_keeps_safety_and_style(self, tmp_workspace):
        result = _build_agents_slim(tmp_workspace)
        assert "Safety Rules" in result
        assert "Response Style" in result
        assert "Workspace Files" in result
        assert "Error Handling" in result

    def test_drops_delegation_and_working_dir(self, tmp_workspace):
        result = _build_agents_slim(tmp_workspace)
        assert "Delegation" not in result
        assert "Working Directory" not in result

    def test_empty_when_no_agents_md(self, tmp_path):
        # Create a workspace dir with no AGENTS.md and no fallback
        empty_ws = tmp_path / "empty_ws"
        empty_ws.mkdir()
        # Patch get_template_content to return empty for this workspace
        from unittest.mock import patch
        with patch(
            "vandelay.agents.prompts.system_prompt.get_template_content",
            return_value="",
        ):
            result = _build_agents_slim(empty_ws)
        assert result == ""


class TestBuildMemberRoster:
    def test_roster_includes_members(self, team_settings):
        result = _build_member_roster(team_settings)
        assert "### cto" in result
        assert "### research" in result

    def test_roster_shows_tools(self, team_settings):
        result = _build_member_roster(team_settings)
        assert "shell" in result
        assert "file" in result
        assert "tavily" in result

    def test_roster_shows_model_override(self, team_settings):
        result = _build_member_roster(team_settings)
        assert "openai / gpt-4o" in result

    def test_roster_shows_inherited(self, team_settings):
        result = _build_member_roster(team_settings)
        assert "inherited" in result

    def test_roster_has_tool_routing(self, team_settings):
        result = _build_member_roster(team_settings)
        assert "Tool Routing" in result

    def test_roster_has_delegation_rules(self, team_settings):
        result = _build_member_roster(team_settings)
        assert "Verify tools" in result
        assert "Never guess" in result

    def test_empty_roster_when_no_members(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=True, members=[]),
            workspace_dir=str(tmp_path),
        )
        result = _build_member_roster(settings)
        assert result == ""

    def test_roster_handles_string_members(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            team=TeamConfig(enabled=True, members=["browser"]),
            workspace_dir=str(tmp_path),
        )
        result = _build_member_roster(settings)
        assert "| browser |" in result


# --- Deep work prompt tests ---


class TestDeepWorkPrompt:
    def test_returns_empty_when_disabled(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=False),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert result == ""

    def test_includes_deep_work_heading(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=True),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert "# Deep Work" in result

    def test_includes_tools_list(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=True),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert "start_deep_work" in result
        assert "check_deep_work_status" in result
        assert "cancel_deep_work" in result

    def test_includes_safeguard_values(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(
                enabled=True,
                max_iterations=25,
                max_time_minutes=120,
                progress_interval_minutes=10,
            ),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert "25" in result
        assert "120" in result
        assert "10" in result

    def test_suggest_activation_mode(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=True, activation="suggest"),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert "suggest" in result.lower() or "confirmation" in result.lower()

    def test_explicit_activation_mode(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=True, activation="explicit"),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert "explicitly" in result.lower()

    def test_auto_activation_mode(self, tmp_path):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=True, activation="auto"),
            workspace_dir=str(tmp_path),
        )
        result = _build_deep_work_prompt(settings)
        assert "automatically" in result.lower()

    def test_injected_into_leader_prompt(self, tmp_workspace):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=True),
            team=TeamConfig(enabled=True, members=["browser"]),
            enabled_tools=[],
            workspace_dir=str(tmp_workspace),
            db_url="",
        )
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=settings,
        )
        assert "Deep Work" in prompt
        assert "start_deep_work" in prompt

    def test_not_injected_when_disabled(self, tmp_workspace):
        settings = Settings(
            agent_name="Test",
            model=ModelConfig(provider="ollama"),
            deep_work=DeepWorkConfig(enabled=False),
            team=TeamConfig(enabled=True, members=["browser"]),
            enabled_tools=[],
            workspace_dir=str(tmp_workspace),
            db_url="",
        )
        prompt = build_team_leader_prompt(
            workspace_dir=tmp_workspace, settings=settings,
        )
        assert "Deep Work" not in prompt


class TestCredentialsSummary:
    """Tests for dynamic credentials summary in system prompt."""

    def test_always_shows_google_status(self):
        """Should always mention Google OAuth status."""
        result = _build_credentials_summary()
        assert "Google OAuth" in result

    def test_shows_configured_env_keys(self, tmp_path, monkeypatch):
        """Should list API keys found in .env file."""
        vandelay_home = tmp_path / ".vandelay"
        vandelay_home.mkdir()
        env_file = vandelay_home / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=sk-test\nTAVILY_API_KEY=tvly-test\n")

        import vandelay.config.constants as consts
        monkeypatch.setattr(consts, "VANDELAY_HOME", vandelay_home)

        result = _build_credentials_summary()
        assert "Anthropic" in result
        assert "Tavily" in result
        # OpenAI not in .env, should not appear
        assert "OpenAI" not in result

    def test_shows_google_authenticated_when_token_exists(self, tmp_path, monkeypatch):
        """Should show Google as authenticated when token file exists."""
        vandelay_home = tmp_path / ".vandelay"
        vandelay_home.mkdir()
        (vandelay_home / "google_token.json").write_text("{}")

        import vandelay.config.constants as consts
        monkeypatch.setattr(consts, "VANDELAY_HOME", vandelay_home)

        result = _build_credentials_summary()
        assert "authenticated" in result

    def test_shows_google_not_set_up_without_token(self, tmp_path, monkeypatch):
        """Should show Google as not set up when no token file."""
        vandelay_home = tmp_path / ".vandelay"
        vandelay_home.mkdir()

        import vandelay.config.constants as consts
        monkeypatch.setattr(consts, "VANDELAY_HOME", vandelay_home)

        result = _build_credentials_summary()
        assert "not set up" in result
