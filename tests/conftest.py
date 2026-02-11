"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory with templates."""
    from vandelay.workspace.manager import init_workspace

    return init_workspace(tmp_path / "workspace")


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Settings configured for testing (no real API calls)."""
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="confirm"),
        workspace_dir=str(tmp_path / "workspace"),
        db_url="",
    )
