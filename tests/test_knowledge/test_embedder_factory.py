"""Tests for the embedder factory auto-resolution logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import EmbedderConfig, KnowledgeConfig, ModelConfig
from vandelay.config.settings import Settings
from vandelay.knowledge.embedder import (
    _build_fastembed,
    _build_ollama,
    _build_openai,
    _build_openrouter,
    create_embedder,
)


def _make_settings(
    provider: str = "openai",
    embedder_provider: str = "",
    embedder_model: str = "",
    embedder_api_key: str = "",
    embedder_base_url: str = "",
    knowledge_enabled: bool = True,
) -> Settings:
    return Settings(
        agent_name="Test",
        model=ModelConfig(provider=provider),
        knowledge=KnowledgeConfig(
            enabled=knowledge_enabled,
            embedder=EmbedderConfig(
                provider=embedder_provider,
                model=embedder_model,
                api_key=embedder_api_key,
                base_url=embedder_base_url,
            ),
        ),
    )


class TestAutoResolution:
    """Test auto-resolving embedder from model provider."""

    def test_openai_provider(self):
        mock_builder = MagicMock(return_value=MagicMock())
        settings = _make_settings(provider="openai")

        with patch.dict(
            "vandelay.knowledge.embedder._EMBEDDER_BUILDERS",
            {"openai": mock_builder},
        ):
            result = create_embedder(settings)
            assert result is mock_builder.return_value
            mock_builder.assert_called_once_with(settings)

    def test_google_provider(self):
        mock_builder = MagicMock(return_value=MagicMock())
        settings = _make_settings(provider="google")

        with patch.dict(
            "vandelay.knowledge.embedder._EMBEDDER_BUILDERS",
            {"google": mock_builder},
        ):
            result = create_embedder(settings)
            assert result is mock_builder.return_value
            mock_builder.assert_called_once_with(settings)

    def test_ollama_provider(self):
        mock_builder = MagicMock(return_value=MagicMock())
        settings = _make_settings(provider="ollama")

        with patch.dict(
            "vandelay.knowledge.embedder._EMBEDDER_BUILDERS",
            {"ollama": mock_builder},
        ):
            result = create_embedder(settings)
            assert result is mock_builder.return_value
            mock_builder.assert_called_once_with(settings)

    def test_anthropic_falls_back_to_fastembed(self):
        """Anthropic has no embeddings API — should fall back to fastembed."""
        settings = _make_settings(provider="anthropic")
        mock_fastembed = MagicMock(return_value=MagicMock())

        with patch(
            "vandelay.knowledge.embedder._build_fastembed",
            mock_fastembed,
        ):
            result = create_embedder(settings)
            assert result is mock_fastembed.return_value
            mock_fastembed.assert_called_once_with(settings)

    def test_openrouter_provider(self):
        mock_builder = MagicMock(return_value=None)
        settings = _make_settings(provider="openrouter")

        with patch.dict(
            "vandelay.knowledge.embedder._EMBEDDER_BUILDERS",
            {"openrouter": mock_builder},
        ):
            result = create_embedder(settings)
            assert result is None
            mock_builder.assert_called_once_with(settings)

    def test_unknown_provider_falls_back_to_fastembed(self):
        settings = _make_settings(provider="unknown_provider")
        mock_fastembed = MagicMock(return_value=MagicMock())

        with patch(
            "vandelay.knowledge.embedder._build_fastembed",
            mock_fastembed,
        ):
            result = create_embedder(settings)
            assert result is mock_fastembed.return_value


class TestExplicitOverride:
    """Test explicit embedder.provider override."""

    def test_override_provider(self):
        """Explicit embedder.provider overrides model.provider."""
        mock_builder = MagicMock(return_value=MagicMock())
        settings = _make_settings(provider="anthropic", embedder_provider="google")

        with patch.dict(
            "vandelay.knowledge.embedder._EMBEDDER_BUILDERS",
            {"google": mock_builder},
        ):
            result = create_embedder(settings)
            assert result is mock_builder.return_value
            mock_builder.assert_called_once_with(settings)

    def test_override_to_ollama(self):
        mock_builder = MagicMock(return_value=MagicMock())
        settings = _make_settings(provider="openai", embedder_provider="ollama")

        with patch.dict(
            "vandelay.knowledge.embedder._EMBEDDER_BUILDERS",
            {"ollama": mock_builder},
        ):
            result = create_embedder(settings)
            assert result is mock_builder.return_value


class TestBuildOpenai:
    def test_with_api_key_config(self):
        settings = _make_settings(
            provider="openai",
            embedder_api_key="sk-custom",
            embedder_model="text-embedding-3-large",
        )
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(OpenAIEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.openai": mock_mod}):
            result = _build_openai(settings)
            assert result is mock_cls.return_value
            mock_cls.assert_called_once_with(
                api_key="sk-custom",
                id="text-embedding-3-large",
            )

    def test_with_env_api_key(self):
        settings = _make_settings(provider="openai")
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(OpenAIEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.openai": mock_mod}):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-from-env"}):
                result = _build_openai(settings)
                assert result is mock_cls.return_value
                call_kwargs = mock_cls.call_args[1]
                assert call_kwargs["api_key"] == "sk-from-env"

    def test_with_base_url(self):
        settings = _make_settings(
            provider="openai",
            embedder_api_key="sk-custom",
            embedder_base_url="https://custom.endpoint",
        )
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(OpenAIEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.openai": mock_mod}):
            result = _build_openai(settings)
            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["base_url"] == "https://custom.endpoint"

    def test_no_api_key_falls_back_to_fastembed(self):
        """Without an API key, OpenAI embedder falls back to fastembed."""
        settings = _make_settings(provider="openai")
        mock_fastembed = MagicMock(return_value=MagicMock())

        with patch.dict("os.environ", {}, clear=True):
            with patch("vandelay.knowledge.embedder._build_fastembed", mock_fastembed):
                result = _build_openai(settings)
                assert result is mock_fastembed.return_value
                mock_fastembed.assert_called_once_with(settings)


class TestBuildOllama:
    def test_default(self):
        settings = _make_settings(provider="ollama")
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(OllamaEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.ollama": mock_mod}):
            result = _build_ollama(settings)
            assert result is mock_cls.return_value
            mock_cls.assert_called_once_with()

    def test_with_model_and_host(self):
        settings = _make_settings(
            provider="ollama",
            embedder_model="nomic-embed-text",
            embedder_base_url="http://localhost:11434",
        )
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(OllamaEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.ollama": mock_mod}):
            result = _build_ollama(settings)
            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["id"] == "nomic-embed-text"
            assert call_kwargs["host"] == "http://localhost:11434"


class TestBuildGoogle:
    def test_with_api_key_config(self):
        from vandelay.knowledge.embedder import _build_google

        settings = _make_settings(provider="google", embedder_api_key="goog-key")
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(GeminiEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.google": mock_mod}):
            result = _build_google(settings)
            assert result is mock_cls.return_value
            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["api_key"] == "goog-key"

    def test_no_api_key_falls_back_to_fastembed(self):
        """Without an API key, Google embedder falls back to fastembed."""
        from vandelay.knowledge.embedder import _build_google

        settings = _make_settings(provider="google")
        mock_fastembed = MagicMock(return_value=MagicMock())

        with patch.dict("os.environ", {}, clear=True):
            with patch("vandelay.knowledge.embedder._build_fastembed", mock_fastembed):
                result = _build_google(settings)
                assert result is mock_fastembed.return_value


class TestBuildFastembed:
    def test_default(self):
        settings = _make_settings(provider="anthropic")
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(FastEmbedEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.fastembed": mock_mod}):
            result = _build_fastembed(settings)
            assert result is mock_cls.return_value
            mock_cls.assert_called_once_with()

    def test_with_custom_model(self):
        settings = _make_settings(
            provider="anthropic",
            embedder_model="BAAI/bge-base-en-v1.5",
        )
        mock_cls = MagicMock(return_value=MagicMock())
        mock_mod = MagicMock(FastEmbedEmbedder=mock_cls)
        with patch.dict("sys.modules", {"agno.knowledge.embedder.fastembed": mock_mod}):
            result = _build_fastembed(settings)
            mock_cls.assert_called_once_with(id="BAAI/bge-base-en-v1.5")

    def test_import_error_returns_none(self):
        """If fastembed package not installed, returns None gracefully."""
        settings = _make_settings(provider="anthropic")
        # Remove the module from sys.modules to simulate missing package
        with patch.dict("sys.modules", {"agno.knowledge.embedder.fastembed": None}):
            result = _build_fastembed(settings)
            assert result is None


class TestBuildOpenrouter:
    def test_explicit_openrouter_falls_back_to_fastembed(self):
        """Explicitly requesting openrouter embedder should try fastembed."""
        settings = _make_settings(provider="openrouter", embedder_provider="openrouter")
        mock_fastembed = MagicMock(return_value=MagicMock())

        with patch(
            "vandelay.knowledge.embedder._build_fastembed",
            mock_fastembed,
        ):
            result = _build_openrouter(settings)
            assert result is mock_fastembed.return_value

    def test_fallback_to_openai_with_key(self):
        """Auto-resolution should try OpenAI if OPENAI_API_KEY is available."""
        mock_builder = MagicMock(return_value=MagicMock())
        settings = _make_settings(provider="openrouter")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            with patch(
                "vandelay.knowledge.embedder._build_openai",
                mock_builder,
            ):
                result = _build_openrouter(settings)
                assert result is mock_builder.return_value

    def test_no_openai_key_falls_back_to_fastembed(self):
        """Without OPENAI_API_KEY, openrouter uses fastembed."""
        settings = _make_settings(provider="openrouter")
        mock_fastembed = MagicMock(return_value=MagicMock())

        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "vandelay.knowledge.embedder._build_fastembed",
                mock_fastembed,
            ):
                result = _build_openrouter(settings)
                assert result is mock_fastembed.return_value
