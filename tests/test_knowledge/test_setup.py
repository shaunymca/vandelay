"""Tests for knowledge setup (create_knowledge)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import EmbedderConfig, KnowledgeConfig, ModelConfig
from vandelay.config.settings import Settings
from vandelay.knowledge.setup import create_knowledge


def _make_settings(
    knowledge_enabled: bool = True,
    provider: str = "openai",
    embedder_provider: str = "",
    workspace_dir: str = "",
) -> Settings:
    return Settings(
        agent_name="Test",
        model=ModelConfig(provider=provider),
        knowledge=KnowledgeConfig(
            enabled=knowledge_enabled,
            embedder=EmbedderConfig(provider=embedder_provider),
        ),
        workspace_dir=workspace_dir or ".",
    )


class TestCreateKnowledge:
    def test_disabled_returns_none(self):
        settings = _make_settings(knowledge_enabled=False)
        assert create_knowledge(settings) is None

    def test_no_embedder_returns_none(self):
        """When no embedder can be created, returns None."""
        settings = _make_settings(provider="anthropic")
        with patch("vandelay.knowledge.setup.create_embedder", return_value=None):
            result = create_knowledge(settings)
            assert result is None

    @patch("vandelay.knowledge.setup.create_embedder")
    def test_embedder_none_returns_none(self, mock_create_embedder):
        mock_create_embedder.return_value = None
        settings = _make_settings()
        result = create_knowledge(settings)
        assert result is None

    @patch("vandelay.knowledge.setup.create_embedder")
    def test_no_vector_db_returns_none(self, mock_create_embedder):
        """Gracefully handle no vector DB available."""
        mock_create_embedder.return_value = MagicMock()
        settings = _make_settings()

        with patch("vandelay.knowledge.vectordb.create_vector_db", return_value=None):
            result = create_knowledge(settings)
            assert result is None

    @patch("vandelay.knowledge.setup.create_embedder")
    def test_success_calls_embedder(self, mock_create_embedder, tmp_path):
        """Verify create_embedder is called with the settings."""
        mock_create_embedder.return_value = MagicMock()
        settings = _make_settings(workspace_dir=str(tmp_path))

        # Even if vector DB creation fails, we verify the embedder check
        try:
            create_knowledge(settings)
        except Exception:
            pass
        mock_create_embedder.assert_called_once_with(settings)

    def test_knowledge_dir_created(self, tmp_path):
        """When knowledge is enabled and embedder is available, knowledge dir is created."""
        settings = _make_settings(workspace_dir=str(tmp_path))

        with (
            patch("vandelay.knowledge.setup.create_embedder", return_value=MagicMock()),
            patch("vandelay.knowledge.vectordb.create_vector_db", return_value=MagicMock()),
        ):
            try:
                create_knowledge(settings)
            except (ImportError, Exception):
                pass

            knowledge_dir = tmp_path / "knowledge"
            assert knowledge_dir.exists()

    @patch("vandelay.knowledge.setup.create_embedder")
    def test_enabled_true_proceeds_to_embedder(self, mock_create_embedder):
        """When enabled=True, create_embedder is called."""
        mock_create_embedder.return_value = None
        settings = _make_settings(knowledge_enabled=True)
        result = create_knowledge(settings)
        assert result is None
        mock_create_embedder.assert_called_once()

    def test_disabled_skips_embedder(self):
        """When enabled=False, no embedder creation is attempted."""
        settings = _make_settings(knowledge_enabled=False)
        with patch("vandelay.knowledge.setup.create_embedder") as mock:
            result = create_knowledge(settings)
            assert result is None
            mock.assert_not_called()
