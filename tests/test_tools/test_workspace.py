"""Tests for the WorkspaceTools agent toolkit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.tools.workspace import WorkspaceTools


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def test_settings(tmp_path: Path, workspace_dir: Path) -> Settings:
    return Settings(
        agent_name="TestAgent",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="trust"),
        workspace_dir=str(workspace_dir),
        enabled_tools=[],
        db_url="",
    )


@pytest.fixture
def toolkit(test_settings: Settings) -> WorkspaceTools:
    return WorkspaceTools(settings=test_settings)


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def toolkit_with_db(test_settings: Settings, mock_db: MagicMock) -> WorkspaceTools:
    return WorkspaceTools(settings=test_settings, db=mock_db)


class TestAppendMethods:
    def test_update_memory_appends_timestamped_entry(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        result = toolkit.update_memory("User likes dark mode")
        assert "Appended to MEMORY.md" in result

        content = (workspace_dir / "MEMORY.md").read_text(encoding="utf-8")
        assert "User likes dark mode" in content
        assert "UTC]" in content  # timestamp present

    def test_update_user_profile_appends(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        result = toolkit.update_user_profile("Name is Shaun")
        assert "Appended to USER.md" in result

        content = (workspace_dir / "USER.md").read_text(encoding="utf-8")
        assert "Name is Shaun" in content

    def test_update_tools_notes_appends(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        result = toolkit.update_tools_notes("Shell runs in trust mode")
        assert "Appended to TOOLS.md" in result

        content = (workspace_dir / "TOOLS.md").read_text(encoding="utf-8")
        assert "Shell runs in trust mode" in content

    def test_creates_file_if_missing(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        """Appending to a file that doesn't exist yet should create it."""
        assert not (workspace_dir / "MEMORY.md").exists()
        toolkit.update_memory("first entry")
        assert (workspace_dir / "MEMORY.md").exists()


class TestReadWorkspaceFile:
    def test_read_allowed_file(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        (workspace_dir / "SOUL.md").write_text("Be helpful.", encoding="utf-8")
        result = toolkit.read_workspace_file("SOUL.md")
        assert "Be helpful." in result

    def test_read_writable_file(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        (workspace_dir / "MEMORY.md").write_text("memories", encoding="utf-8")
        result = toolkit.read_workspace_file("MEMORY.md")
        assert "memories" in result

    def test_read_disallowed_file_rejected(self, toolkit: WorkspaceTools):
        result = toolkit.read_workspace_file("secret.txt")
        assert "Error" in result
        assert "not a valid workspace file" in result

    def test_read_path_traversal_rejected(self, toolkit: WorkspaceTools):
        result = toolkit.read_workspace_file("../../etc/passwd")
        assert "Error" in result

    def test_read_missing_file(self, toolkit: WorkspaceTools):
        result = toolkit.read_workspace_file("MEMORY.md")
        assert "does not exist" in result


class TestReplaceWorkspaceFile:
    def test_replace_writable_file(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        (workspace_dir / "MEMORY.md").write_text("old stuff", encoding="utf-8")
        result = toolkit.replace_workspace_file("MEMORY.md", "# Fresh Start\n")
        assert "Replaced MEMORY.md" in result

        content = (workspace_dir / "MEMORY.md").read_text(encoding="utf-8")
        assert content == "# Fresh Start\n"
        assert "old stuff" not in content

    def test_replace_readonly_file_rejected(self, toolkit: WorkspaceTools):
        result = toolkit.replace_workspace_file("SOUL.md", "hacked")
        assert "Error" in result
        assert "read-only" in result

    def test_replace_agents_rejected(self, toolkit: WorkspaceTools):
        result = toolkit.replace_workspace_file("AGENTS.md", "hacked")
        assert "Error" in result

    def test_replace_creates_file_if_missing(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        result = toolkit.replace_workspace_file("TOOLS.md", "# Tools\n")
        assert "Replaced TOOLS.md" in result
        assert (workspace_dir / "TOOLS.md").exists()


class TestDbBackedMemory:
    def test_update_memory_uses_db_when_available(
        self, toolkit_with_db: WorkspaceTools, mock_db: MagicMock, workspace_dir: Path
    ):
        result = toolkit_with_db.update_memory("User likes dark mode")
        assert "Memory saved" in result
        mock_db.upsert_user_memory.assert_called_once()

        memory = mock_db.upsert_user_memory.call_args[0][0]
        assert memory.memory == "User likes dark mode"
        assert memory.topics == ["workspace_memory"]

        # Should NOT have written to file
        assert not (workspace_dir / "MEMORY.md").exists()

    def test_update_memory_falls_back_to_file_without_db(
        self, toolkit: WorkspaceTools, workspace_dir: Path
    ):
        result = toolkit.update_memory("Fallback entry")
        assert "Appended to MEMORY.md" in result
        assert (workspace_dir / "MEMORY.md").exists()

    def test_update_memory_falls_back_on_db_error(
        self, toolkit_with_db: WorkspaceTools, mock_db: MagicMock, workspace_dir: Path
    ):
        mock_db.upsert_user_memory.side_effect = RuntimeError("DB error")
        result = toolkit_with_db.update_memory("Error entry")
        assert "Appended to MEMORY.md" in result
        assert (workspace_dir / "MEMORY.md").exists()

    def test_other_append_methods_unaffected_by_db(
        self, toolkit_with_db: WorkspaceTools, mock_db: MagicMock, workspace_dir: Path
    ):
        """update_user_profile and update_tools_notes should still use file append."""
        toolkit_with_db.update_user_profile("Name is Shaun")
        assert (workspace_dir / "USER.md").exists()
        mock_db.upsert_user_memory.assert_not_called()
