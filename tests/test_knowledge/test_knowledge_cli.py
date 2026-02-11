"""Tests for knowledge CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vandelay.cli.knowledge_commands import (
    SUPPORTED_EXTENSIONS,
    _find_supported_files,
    app,
)

runner = CliRunner()


class TestFindSupportedFiles:
    def test_single_file_supported(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello")
        result = _find_supported_files(f)
        assert result == [f]

    def test_single_file_unsupported(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("hello")
        result = _find_supported_files(f)
        assert result == []

    def test_directory_recursive(self, tmp_path):
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.pdf").write_text("c")
        (sub / "d.xyz").write_text("d")  # unsupported

        result = _find_supported_files(tmp_path)
        names = {f.name for f in result}
        assert "a.md" in names
        assert "b.txt" in names
        assert "c.pdf" in names
        assert "d.xyz" not in names

    def test_empty_directory(self, tmp_path):
        result = _find_supported_files(tmp_path)
        assert result == []


class TestSupportedExtensions:
    def test_contains_common_types(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS
        assert ".json" in SUPPORTED_EXTENSIONS


class TestKnowledgeStatusCommand:
    @patch("vandelay.cli.knowledge_commands._get_settings")
    def test_status_disabled(self, mock_settings):
        settings = MagicMock()
        settings.knowledge.enabled = False
        mock_settings.return_value = settings

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "no" in result.output.lower() or "disabled" in result.output.lower()

    @patch("vandelay.knowledge.embedder.create_embedder")
    @patch("vandelay.cli.knowledge_commands._get_settings")
    def test_status_enabled(self, mock_settings, mock_embedder):
        settings = MagicMock()
        settings.knowledge.enabled = True
        settings.knowledge.embedder.provider = "openai"
        settings.knowledge.embedder.model = ""
        settings.model.provider = "openai"
        settings.workspace_dir = "/tmp/test"
        mock_settings.return_value = settings
        mock_embedder.return_value = None

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "openai" in result.output.lower()


class TestKnowledgeAddCommand:
    def test_path_not_found(self):
        result = runner.invoke(app, ["add", "/nonexistent/path/abc123"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_no_supported_files(self, tmp_path):
        (tmp_path / "test.xyz").write_text("hello")
        result = runner.invoke(app, ["add", str(tmp_path)])
        assert result.exit_code == 1
        assert "no supported files" in result.output.lower()


class TestKnowledgeClearCommand:
    @patch("vandelay.cli.knowledge_commands._ensure_knowledge")
    def test_clear_cancelled(self, mock_ensure):
        """Clear without --yes should prompt; we simulate 'n'."""
        mock_ensure.return_value = (MagicMock(), MagicMock())
        result = runner.invoke(app, ["clear"], input="n\n")
        assert "cancelled" in result.output.lower() or result.exit_code != 0
