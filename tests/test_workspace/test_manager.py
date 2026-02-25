"""Tests for workspace manager — template content loading and initialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from vandelay.workspace.manager import get_template_content, init_workspace


class TestGetTemplateContent:
    """get_template_content() returns correct content with fallback logic."""

    def test_returns_user_file_when_content_present(self, tmp_path: Path):
        """User file with content takes priority over template."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "HEARTBEAT.md").write_text("# Custom\nMy custom heartbeat.", encoding="utf-8")

        result = get_template_content("HEARTBEAT.md", workspace_dir=ws)
        assert result == "# Custom\nMy custom heartbeat."

    def test_falls_back_to_template_when_user_file_missing(self, tmp_path: Path):
        """When user file doesn't exist, shipped template is returned."""
        ws = tmp_path / "workspace"
        ws.mkdir()

        result = get_template_content("HEARTBEAT.md", workspace_dir=ws)
        # Template has content (not empty)
        assert result.strip()
        assert "Heartbeat" in result or "heartbeat" in result.lower()

    def test_falls_back_to_template_when_user_file_is_empty(self, tmp_path: Path):
        """When user file exists but is empty, shipped template is returned.

        This is the bug fix: previously an empty user file would suppress the
        shipped template, leaving the agent without HEARTBEAT.md instructions.
        """
        ws = tmp_path / "workspace"
        ws.mkdir()
        # Simulate a zero-byte HEARTBEAT.md (as seen on production after PR #69)
        (ws / "HEARTBEAT.md").write_text("", encoding="utf-8")

        result = get_template_content("HEARTBEAT.md", workspace_dir=ws)
        # Should return the shipped template, not the empty string
        assert result.strip()
        assert "HEARTBEAT_OK" in result

    def test_falls_back_to_template_when_user_file_is_whitespace_only(self, tmp_path: Path):
        """Whitespace-only user file triggers the same fallback."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "HEARTBEAT.md").write_text("   \n\t\n", encoding="utf-8")

        result = get_template_content("HEARTBEAT.md", workspace_dir=ws)
        assert result.strip()
        assert "HEARTBEAT_OK" in result

    def test_returns_empty_string_when_neither_file_exists(self, tmp_path: Path):
        """Returns empty string only if both user file and template are missing."""
        ws = tmp_path / "workspace"
        ws.mkdir()

        result = get_template_content("NONEXISTENT_FILE.md", workspace_dir=ws)
        assert result == ""

    def test_user_content_preserved_for_non_heartbeat_files(self, tmp_path: Path):
        """Non-empty user files always take priority (e.g. SOUL.md customization)."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("# My Custom Soul\nI am unique.", encoding="utf-8")

        result = get_template_content("SOUL.md", workspace_dir=ws)
        assert "My Custom Soul" in result


class TestInitWorkspace:
    """init_workspace() creates directories and copies templates if missing."""

    def test_creates_workspace_directory(self, tmp_path: Path):
        """init_workspace() creates the workspace dir if it doesn't exist."""
        ws = tmp_path / "ws"
        assert not ws.exists()
        init_workspace(workspace_dir=ws)
        assert ws.exists()

    def test_copies_templates_when_missing(self, tmp_path: Path):
        """Template files are copied on first init."""
        ws = tmp_path / "ws"
        init_workspace(workspace_dir=ws)
        assert (ws / "HEARTBEAT.md").exists()
        assert (ws / "SOUL.md").exists()

    def test_does_not_overwrite_existing_user_files(self, tmp_path: Path):
        """Existing user files are never overwritten by init_workspace."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "HEARTBEAT.md").write_text("# My custom checklist", encoding="utf-8")

        init_workspace(workspace_dir=ws)

        # User's customization should be preserved
        assert (ws / "HEARTBEAT.md").read_text(encoding="utf-8") == "# My custom checklist"

    def test_creates_memory_subdirectory(self, tmp_path: Path):
        """The memory/ subdirectory is created inside the workspace."""
        ws = tmp_path / "ws"
        init_workspace(workspace_dir=ws)
        assert (ws / "memory").is_dir()
