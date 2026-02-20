"""Tests for the model catalog."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

from vandelay.models.catalog import (
    ModelOption,
    ProviderInfo,
    fetch_ollama_models,
    fetch_provider_models,
    get_model_choices,
    get_provider,
    get_providers,
)


class TestProviderCatalog:
    def test_all_10_providers_present(self):
        providers = get_providers()
        expected = {
            "anthropic", "openai", "google", "groq", "deepseek",
            "mistral", "together", "xai", "openrouter", "ollama",
        }
        assert set(providers.keys()) == expected

    def test_each_provider_has_models(self):
        for key, info in get_providers().items():
            assert len(info.models) >= 2, f"{key} should have at least 2 models"

    def test_each_provider_has_recommended_tier(self):
        for key, info in get_providers().items():
            tiers = {m.tier for m in info.models}
            assert "recommended" in tiers, f"{key} missing a 'recommended' model"

    def test_ollama_has_no_env_key(self):
        info = get_provider("ollama")
        assert info is not None
        assert info.env_key is None

    def test_non_ollama_providers_have_env_key(self):
        for key, info in get_providers().items():
            if key != "ollama":
                assert info.env_key is not None, f"{key} should have an env_key"

    def test_get_model_choices_returns_list(self):
        choices = get_model_choices("anthropic")
        assert len(choices) >= 2
        assert all(isinstance(m, ModelOption) for m in choices)

    def test_get_model_choices_unknown_provider(self):
        choices = get_model_choices("nonexistent")
        assert choices == []

    def test_get_provider_unknown(self):
        assert get_provider("nonexistent") is None

    def test_provider_info_fields(self):
        info = get_provider("anthropic")
        assert isinstance(info, ProviderInfo)
        assert info.name == "Anthropic (Claude)"
        assert info.env_key == "ANTHROPIC_API_KEY"
        assert "console.anthropic.com" in info.api_key_help


class TestFetchOllamaModels:
    def test_connection_refused_returns_empty(self):
        """Unreachable server should return empty list quickly."""
        import urllib.request

        with patch.object(
            urllib.request, "urlopen", side_effect=OSError("Connection refused"),
        ):
            result = fetch_ollama_models(timeout=0.1)
            assert result == []

    def test_successful_fetch(self):
        """Mock a successful Ollama /api/tags response."""
        mock_data = json.dumps({
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "mistral:7b"},
            ]
        }).encode()

        mock_response = MagicMock()
        mock_response.read.return_value = mock_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        import urllib.request

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_ollama_models(timeout=2.0)
            assert len(result) == 2
            assert result[0].id == "llama3.1:latest"
            assert result[1].id == "mistral:7b"
            assert all(m.tier == "local" for m in result)

    def test_invalid_json_returns_empty(self):
        """Malformed JSON should return empty list."""
        import urllib.request

        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_ollama_models(timeout=0.1)
            assert result == []


class TestFetchProviderModels:
    """Tests for live model fetching from provider APIs."""

    def _mock_response(self, data: dict | list) -> MagicMock:
        mock = MagicMock()
        mock.read.return_value = json.dumps(data).encode()
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    def test_anthropic_models(self):
        import urllib.request

        data = {
            "data": [
                {"id": "claude-sonnet-4-5-20250929", "display_name": "Claude Sonnet 4.5"},
                {"id": "claude-haiku-4-5-20251001", "display_name": "Claude Haiku 4.5"},
                {"id": "text-embedding-3", "display_name": "Embeddings"},  # should be filtered
            ]
        }
        with patch.object(urllib.request, "urlopen", return_value=self._mock_response(data)):
            result = fetch_provider_models("anthropic", "sk-test")
        # Only claude models should appear
        ids = [m.id for m in result]
        assert "claude-sonnet-4-5-20250929" in ids
        assert "claude-haiku-4-5-20251001" in ids
        assert "text-embedding-3" not in ids

    def test_openai_compatible_models(self):
        import urllib.request

        data = {
            "data": [
                {"id": "gpt-4o", "object": "model"},
                {"id": "gpt-4o-mini", "object": "model"},
                {"id": "text-embedding-ada-002", "object": "model"},  # filtered
                {"id": "whisper-1", "object": "model"},  # filtered
                {"id": "dall-e-3", "object": "model"},  # filtered
            ]
        }
        with patch.object(urllib.request, "urlopen", return_value=self._mock_response(data)):
            result = fetch_provider_models("openai", "sk-test")
        ids = [m.id for m in result]
        assert "gpt-4o" in ids
        assert "gpt-4o-mini" in ids
        assert "text-embedding-ada-002" not in ids
        assert "whisper-1" not in ids
        assert "dall-e-3" not in ids

    def test_google_models(self):
        import urllib.request

        data = {
            "models": [
                {
                    "name": "models/gemini-2.0-flash",
                    "displayName": "Gemini 2.0 Flash",
                    "supportedGenerationMethods": ["generateContent"],
                },
                {
                    "name": "models/embedding-001",
                    "displayName": "Embedding",
                    "supportedGenerationMethods": ["embedContent"],
                },
            ]
        }
        with patch.object(urllib.request, "urlopen", return_value=self._mock_response(data)):
            result = fetch_provider_models("google", "test-key")
        ids = [m.id for m in result]
        assert "gemini-2.0-flash" in ids
        assert "embedding-001" not in ids

    def test_together_chat_filter(self):
        import urllib.request

        data = [
            {"id": "meta-llama/Llama-3-70b-chat-hf", "type": "chat",
             "display_name": "Llama 3 70B"},
            {"id": "some-embedding-model", "type": "embedding",
             "display_name": "Embedding"},
        ]
        with patch.object(urllib.request, "urlopen", return_value=self._mock_response(data)):
            result = fetch_provider_models("together", "test-key")
        assert len(result) == 1
        assert result[0].id == "meta-llama/Llama-3-70b-chat-hf"

    def test_connection_error_returns_empty(self):
        import urllib.request

        with patch.object(urllib.request, "urlopen", side_effect=OSError("refused")):
            result = fetch_provider_models("anthropic", "sk-test", timeout=0.1)
        assert result == []

    def test_unknown_provider_returns_empty(self):
        result = fetch_provider_models("nonexistent", "key")
        assert result == []

    def test_no_api_key_returns_empty(self):
        result = fetch_provider_models("anthropic", "")
        assert result == []
