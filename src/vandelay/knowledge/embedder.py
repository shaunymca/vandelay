"""Embedder factory — auto-resolves an embedder from the model provider."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)


def create_embedder(settings: Settings) -> Any | None:
    """Create an Agno embedder based on settings.

    Resolution order:
      1. Explicit ``knowledge.embedder.provider`` → use that provider
      2. Derive from ``model.provider`` (openai→OpenAI, google→Gemini, etc.)
      3. Return ``None`` when no embedder can be created

    Returns:
        An Agno Embedder instance, or ``None`` if unavailable.
    """
    ecfg = settings.knowledge.embedder
    provider = ecfg.provider or settings.model.provider

    builder = _EMBEDDER_BUILDERS.get(provider)
    if builder is None:
        logger.warning(
            "No embedder available for provider '%s'. "
            "Knowledge requires an embedder. Set knowledge.embedder.provider in config.",
            provider,
        )
        return None

    return builder(settings)


# ---------------------------------------------------------------------------
# Per-provider builder functions
# ---------------------------------------------------------------------------


def _build_openai(settings: Settings) -> Any | None:
    ecfg = settings.knowledge.embedder
    try:
        from agno.embedder.openai import OpenAIEmbedder
    except ImportError:
        logger.warning("openai package not installed — cannot create OpenAI embedder.")
        return None

    kwargs: dict[str, Any] = {}
    api_key = ecfg.api_key or os.environ.get("OPENAI_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key
    if ecfg.model:
        kwargs["id"] = ecfg.model
    if ecfg.base_url:
        kwargs["base_url"] = ecfg.base_url
    return OpenAIEmbedder(**kwargs)


def _build_google(settings: Settings) -> Any | None:
    ecfg = settings.knowledge.embedder
    try:
        from agno.embedder.google import GeminiEmbedder
    except ImportError:
        logger.warning("google-genai package not installed — cannot create Gemini embedder.")
        return None

    kwargs: dict[str, Any] = {}
    api_key = ecfg.api_key or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key
    if ecfg.model:
        kwargs["id"] = ecfg.model
    return GeminiEmbedder(**kwargs)


def _build_ollama(settings: Settings) -> Any | None:
    ecfg = settings.knowledge.embedder
    try:
        from agno.embedder.ollama import OllamaEmbedder
    except ImportError:
        logger.warning("ollama package not installed — cannot create Ollama embedder.")
        return None

    kwargs: dict[str, Any] = {}
    if ecfg.model:
        kwargs["id"] = ecfg.model
    if ecfg.base_url:
        kwargs["host"] = ecfg.base_url
    return OllamaEmbedder(**kwargs)


def _build_openrouter(settings: Settings) -> Any | None:
    """OpenRouter doesn't have its own embedder — fall back to OpenAI if available."""
    if settings.knowledge.embedder.provider == "openrouter":
        # Explicit request for openrouter embedder — not supported
        logger.warning(
            "OpenRouter does not provide an embeddings API. "
            "Set knowledge.embedder.provider to 'openai', 'google', or 'ollama'."
        )
        return None
    # Auto-resolution path: try OpenAI if API key is available
    if os.environ.get("OPENAI_API_KEY"):
        return _build_openai(settings)
    logger.warning(
        "OpenRouter model detected but no OPENAI_API_KEY for embeddings. "
        "Set knowledge.embedder.provider in config."
    )
    return None


_EMBEDDER_BUILDERS = {
    "openai": _build_openai,
    "google": _build_google,
    "ollama": _build_ollama,
    "openrouter": _build_openrouter,
    # anthropic intentionally omitted — no embeddings API
}
