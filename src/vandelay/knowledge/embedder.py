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
      3. Providers without an embedding API (anthropic) fall back to fastembed
      4. Return ``None`` when no embedder can be created

    Returns:
        An Agno Embedder instance, or ``None`` if unavailable.
    """
    ecfg = settings.knowledge.embedder
    provider = ecfg.provider or settings.model.provider

    builder = _EMBEDDER_BUILDERS.get(provider)
    if builder is None:
        # Provider has no embedder (e.g. anthropic) — try fastembed as fallback
        logger.info(
            "No native embedder for provider '%s'. Trying local fastembed fallback.",
            provider,
        )
        return _build_fastembed(settings)

    return builder(settings)


# ---------------------------------------------------------------------------
# Per-provider builder functions
# ---------------------------------------------------------------------------


def _build_openai(settings: Settings) -> Any | None:
    ecfg = settings.knowledge.embedder
    api_key = ecfg.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.info("No OPENAI_API_KEY found — falling back to local fastembed embedder.")
        return _build_fastembed(settings)

    try:
        from agno.knowledge.embedder.openai import OpenAIEmbedder
    except ImportError:
        logger.warning("openai package not installed — falling back to local fastembed embedder.")
        return _build_fastembed(settings)

    kwargs: dict[str, Any] = {"api_key": api_key}
    if ecfg.model:
        kwargs["id"] = ecfg.model
    if ecfg.base_url:
        kwargs["base_url"] = ecfg.base_url
    return OpenAIEmbedder(**kwargs)


def _build_google(settings: Settings) -> Any | None:
    ecfg = settings.knowledge.embedder
    api_key = ecfg.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.info("No GOOGLE_API_KEY found — falling back to local fastembed embedder.")
        return _build_fastembed(settings)

    try:
        from agno.knowledge.embedder.google import GeminiEmbedder
    except ImportError:
        logger.warning("google-genai package not installed — falling back to local fastembed embedder.")
        return _build_fastembed(settings)

    kwargs: dict[str, Any] = {"api_key": api_key}
    if ecfg.model:
        kwargs["id"] = ecfg.model
    return GeminiEmbedder(**kwargs)


def _build_ollama(settings: Settings) -> Any | None:
    ecfg = settings.knowledge.embedder
    try:
        from agno.knowledge.embedder.ollama import OllamaEmbedder
    except ImportError:
        logger.warning("ollama package not installed — cannot create Ollama embedder.")
        return None

    kwargs: dict[str, Any] = {}
    if ecfg.model:
        kwargs["id"] = ecfg.model
    if ecfg.base_url:
        kwargs["host"] = ecfg.base_url
    return OllamaEmbedder(**kwargs)


def _build_fastembed(settings: Settings) -> Any | None:
    """Local embedder via fastembed — no API key required."""
    ecfg = settings.knowledge.embedder
    try:
        from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
    except ImportError:
        logger.warning(
            "fastembed is not installed — local embedder unavailable. "
            "Knowledge will be disabled. To enable it without an API key, run: "
            "uv add fastembed  (requires onnxruntime; may not work on Intel Mac). "
            "Alternatively, set an OpenAI or Google API key to use a hosted embedder."
        )
        return None

    kwargs: dict[str, Any] = {}
    if ecfg.model:
        kwargs["id"] = ecfg.model
    # Default: BAAI/bge-small-en-v1.5 (384 dims, fast, no API key)
    return FastEmbedEmbedder(**kwargs)


def _build_openrouter(settings: Settings) -> Any | None:
    """OpenRouter doesn't have its own embedder — fall back to OpenAI or fastembed."""
    if settings.knowledge.embedder.provider == "openrouter":
        # Explicit request for openrouter embedder — not supported
        logger.warning(
            "OpenRouter does not provide an embeddings API. "
            "Trying fastembed fallback."
        )
        return _build_fastembed(settings)
    # Auto-resolution path: try OpenAI if API key is available, else fastembed
    if os.environ.get("OPENAI_API_KEY"):
        return _build_openai(settings)
    logger.info(
        "OpenRouter model detected, no OPENAI_API_KEY. Using local fastembed embedder."
    )
    return _build_fastembed(settings)


_EMBEDDER_BUILDERS = {
    "openai": _build_openai,
    "google": _build_google,
    "ollama": _build_ollama,
    "openrouter": _build_openrouter,
    "fastembed": _build_fastembed,
    # anthropic intentionally omitted — falls through to fastembed in create_embedder()
}
