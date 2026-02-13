"""LLM Router — instantiates and caches models per complexity tier."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vandelay.config.settings import Settings
    from vandelay.routing.config import RouterConfig

logger = logging.getLogger("vandelay.routing")


class LLMRouter:
    """Per-tier model instantiation with caching.

    Each tier (e.g. "simple", "complex") gets its own model instance,
    created on first use and reused thereafter.
    """

    def __init__(self, config: RouterConfig, settings: Settings) -> None:
        self._config = config
        self._settings = settings
        self._cache: dict[str, Any] = {}

    def get_model_for_tier(self, tier: str) -> Any:
        """Return the model instance for *tier*, creating it on first call.

        Falls back to the default model from settings if the tier is unknown.
        """
        if tier in self._cache:
            return self._cache[tier]

        tier_cfg = self._config.tiers.get(tier)
        if tier_cfg is None or not tier_cfg.provider or not tier_cfg.model_id:
            logger.warning("Unknown or unconfigured tier '%s', using default model", tier)
            from vandelay.agents.factory import _get_model
            model = _get_model(self._settings)
            self._cache[tier] = model
            return model

        model = self._create_model(tier_cfg.provider, tier_cfg.model_id)
        self._cache[tier] = model
        logger.info("Created %s model for tier '%s': %s", tier_cfg.provider, tier, tier_cfg.model_id)
        return model

    def _create_model(self, provider: str, model_id: str) -> Any:
        """Instantiate a model from provider/model_id using the same logic as factory."""
        from vandelay.agents.factory import _load_env

        _load_env()

        import os

        if provider == "anthropic":
            from agno.models.anthropic import Claude
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            return Claude(id=model_id, api_key=api_key) if api_key else Claude(id=model_id)

        if provider == "openai":
            from agno.models.openai import OpenAIChat
            return OpenAIChat(id=model_id)

        if provider == "google":
            from agno.models.google import Gemini
            return Gemini(id=model_id)

        if provider == "ollama":
            from agno.models.ollama import Ollama
            return Ollama(id=model_id)

        if provider == "openrouter":
            from agno.models.openai import OpenAIChat
            api_key = os.environ.get("OPENROUTER_API_KEY")
            return OpenAIChat(
                id=model_id,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )

        raise ValueError(f"Unknown router model provider: {provider}")
