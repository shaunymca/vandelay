"""Tests for system prompt builder."""

from pathlib import Path

import pytest

from vandelay.agents.prompts.system_prompt import build_system_prompt
from vandelay.config.models import ModelConfig, SafetyConfig
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
    """Prompt should include the dynamic tool catalog when settings provided."""
    prompt = build_system_prompt(
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    assert "Available Tool Catalog" in prompt
    assert "enable_tool" in prompt


def test_build_prompt_catalog_shows_enabled(tmp_workspace, prompt_settings):
    """Tool catalog should mark enabled tools."""
    prompt = build_system_prompt(
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    assert "shell [ENABLED]" in prompt
    assert "file [ENABLED]" in prompt


def test_build_prompt_catalog_shows_available(tmp_workspace, prompt_settings):
    """Tool catalog should mark non-enabled tools as available."""
    prompt = build_system_prompt(
        workspace_dir=tmp_workspace,
        settings=prompt_settings,
    )
    assert "[available]" in prompt


def test_build_prompt_no_catalog_without_settings(tmp_workspace):
    """Without settings, no tool catalog should appear."""
    prompt = build_system_prompt(workspace_dir=tmp_workspace)
    assert "Available Tool Catalog" not in prompt
