"""Tests for the LLM Router."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.routing.config import RouterConfig, TierConfig
from vandelay.routing.router import LLMRouter


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestAgent",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="trust"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=[],
        db_url="",
    )


@pytest.fixture
def router_config() -> RouterConfig:
    return RouterConfig(
        enabled=True,
        tiers={
            "simple": TierConfig(provider="ollama", model_id="llama3.2:1b"),
            "complex": TierConfig(provider="ollama", model_id="llama3.1"),
        },
    )


class TestLLMRouter:
    @patch("vandelay.routing.router.LLMRouter._create_model")
    def test_get_model_creates_and_caches(
        self, mock_create, router_config, test_settings
    ):
        mock_model = MagicMock()
        mock_create.return_value = mock_model

        router = LLMRouter(router_config, test_settings)
        model1 = router.get_model_for_tier("simple")
        model2 = router.get_model_for_tier("simple")

        assert model1 is model2
        mock_create.assert_called_once_with("ollama", "llama3.2:1b")

    @patch("vandelay.routing.router.LLMRouter._create_model")
    def test_different_tiers_get_different_models(
        self, mock_create, router_config, test_settings
    ):
        simple_model = MagicMock()
        complex_model = MagicMock()
        mock_create.side_effect = [simple_model, complex_model]

        router = LLMRouter(router_config, test_settings)
        m1 = router.get_model_for_tier("simple")
        m2 = router.get_model_for_tier("complex")

        assert m1 is not m2
        assert mock_create.call_count == 2

    @patch("vandelay.agents.factory._get_model")
    def test_unknown_tier_falls_back_to_default(
        self, mock_get_model, router_config, test_settings
    ):
        fallback = MagicMock()
        mock_get_model.return_value = fallback

        router = LLMRouter(router_config, test_settings)
        model = router.get_model_for_tier("unknown_tier")

        assert model is fallback
        mock_get_model.assert_called_once_with(test_settings)

    @patch("vandelay.routing.router.LLMRouter._create_model")
    def test_empty_provider_falls_back(
        self, mock_create, test_settings
    ):
        config = RouterConfig(
            enabled=True,
            tiers={"simple": TierConfig(provider="", model_id="")},
        )
        with patch("vandelay.agents.factory._get_model") as mock_default:
            mock_default.return_value = MagicMock()
            router = LLMRouter(config, test_settings)
            router.get_model_for_tier("simple")
            mock_default.assert_called_once()
        mock_create.assert_not_called()
