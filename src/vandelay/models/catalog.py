"""Curated model catalog — providers and their recommended models."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModelOption:
    """A single model choice within a provider."""

    id: str          # e.g. "claude-sonnet-4-5-20250929"
    label: str       # e.g. "Claude Sonnet 4.5"
    tier: str        # "recommended" | "flagship" | "fast"


@dataclass
class ProviderInfo:
    """Everything needed to configure a provider during onboarding."""

    name: str                    # "Anthropic (Claude)"
    env_key: str | None          # "ANTHROPIC_API_KEY" (None for Ollama)
    api_key_help: str            # "Get one at: console.anthropic.com/settings/keys"
    models: list[ModelOption] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Provider catalog — 10 curated providers
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, ProviderInfo] = {
    "anthropic": ProviderInfo(
        name="Anthropic (Claude)",
        env_key="ANTHROPIC_API_KEY",
        api_key_help="Get one at: console.anthropic.com/settings/keys",
        models=[
            ModelOption("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5", "recommended"),
            ModelOption("claude-opus-4-5-20250929", "Claude Opus 4.5", "flagship"),
            ModelOption("claude-haiku-4-5-20251001", "Claude Haiku 4.5", "fast"),
        ],
    ),
    "openai": ProviderInfo(
        name="OpenAI (GPT)",
        env_key="OPENAI_API_KEY",
        api_key_help="Get one at: platform.openai.com/api-keys",
        models=[
            ModelOption("gpt-4o", "GPT-4o", "recommended"),
            ModelOption("gpt-4.1", "GPT-4.1", "flagship"),
            ModelOption("gpt-4o-mini", "GPT-4o Mini", "fast"),
            ModelOption("o3-mini", "o3-mini (reasoning)", "flagship"),
        ],
    ),
    "openai-codex": ProviderInfo(
        name="ChatGPT Plus/Pro (Codex OAuth)",
        env_key=None,
        api_key_help="Run `npm install -g @openai/codex && codex login` first.",
        models=[
            ModelOption("gpt-5.1-codex-mini", "GPT-5.1 Codex Mini", "recommended"),
            ModelOption("gpt-5.2-codex", "GPT-5.2 Codex", "flagship"),
            ModelOption("gpt-5.1", "GPT-5.1", "fast"),
        ],
    ),
    "google": ProviderInfo(
        name="Google (Gemini)",
        env_key="GOOGLE_API_KEY",
        api_key_help="Get one at: aistudio.google.com/apikey",
        models=[
            ModelOption("gemini-2.0-flash", "Gemini 2.0 Flash", "recommended"),
            ModelOption("gemini-2.5-pro-preview-06-05", "Gemini 2.5 Pro", "flagship"),
            ModelOption("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite", "fast"),
        ],
    ),
    "groq": ProviderInfo(
        name="Groq (fast inference)",
        env_key="GROQ_API_KEY",
        api_key_help="Get one at: console.groq.com/keys",
        models=[
            ModelOption("llama-3.3-70b-versatile", "Llama 3.3 70B", "recommended"),
            ModelOption("llama-3.1-8b-instant", "Llama 3.1 8B Instant", "fast"),
            ModelOption("mixtral-8x7b-32768", "Mixtral 8x7B", "fast"),
        ],
    ),
    "deepseek": ProviderInfo(
        name="DeepSeek",
        env_key="DEEPSEEK_API_KEY",
        api_key_help="Get one at: platform.deepseek.com/api_keys",
        models=[
            ModelOption("deepseek-chat", "DeepSeek Chat (V3)", "recommended"),
            ModelOption("deepseek-reasoner", "DeepSeek Reasoner (R1)", "flagship"),
        ],
    ),
    "mistral": ProviderInfo(
        name="Mistral",
        env_key="MISTRAL_API_KEY",
        api_key_help="Get one at: console.mistral.ai/api-keys",
        models=[
            ModelOption("mistral-large-latest", "Mistral Large", "recommended"),
            ModelOption("mistral-small-latest", "Mistral Small", "fast"),
            ModelOption("codestral-latest", "Codestral", "flagship"),
        ],
    ),
    "together": ProviderInfo(
        name="Together (open source)",
        env_key="TOGETHER_API_KEY",
        api_key_help="Get one at: api.together.xyz/settings/api-keys",
        models=[
            ModelOption(
                "meta-llama/Llama-3-70b-chat-hf", "Llama 3 70B", "recommended",
            ),
            ModelOption(
                "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                "Llama 3.1 405B",
                "flagship",
            ),
            ModelOption(
                "mistralai/Mixtral-8x7B-Instruct-v0.1", "Mixtral 8x7B", "fast",
            ),
        ],
    ),
    "xai": ProviderInfo(
        name="xAI (Grok)",
        env_key="XAI_API_KEY",
        api_key_help="Get one at: console.x.ai",
        models=[
            ModelOption("grok-2", "Grok 2", "recommended"),
            ModelOption("grok-2-mini", "Grok 2 Mini", "fast"),
        ],
    ),
    "openrouter": ProviderInfo(
        name="OpenRouter (multi-provider gateway)",
        env_key="OPENROUTER_API_KEY",
        api_key_help="Get one at: openrouter.ai/keys",
        models=[
            ModelOption(
                "anthropic/claude-sonnet-4-5-20250929",
                "Claude Sonnet 4.5",
                "recommended",
            ),
            ModelOption("openai/gpt-4o", "GPT-4o", "flagship"),
            ModelOption(
                "google/gemini-2.0-flash-001", "Gemini 2.0 Flash", "fast",
            ),
            ModelOption("deepseek/deepseek-chat", "DeepSeek V3", "fast"),
        ],
    ),
    "ollama": ProviderInfo(
        name="Ollama (local, no API key)",
        env_key=None,
        api_key_help="Install from: ollama.com — then run: ollama pull llama3.1",
        models=[
            ModelOption("llama3.1", "Llama 3.1 8B", "recommended"),
            ModelOption("llama3.1:70b", "Llama 3.1 70B", "flagship"),
            ModelOption("mistral", "Mistral 7B", "fast"),
            ModelOption("phi3", "Phi-3 Mini", "fast"),
        ],
    ),
}


def get_providers() -> dict[str, ProviderInfo]:
    """Return all available providers."""
    return dict(_PROVIDERS)


def get_provider(key: str) -> ProviderInfo | None:
    """Return a single provider by key, or None."""
    return _PROVIDERS.get(key)


def get_model_choices(provider: str) -> list[ModelOption]:
    """Return curated model list for a provider."""
    info = _PROVIDERS.get(provider)
    return list(info.models) if info else []


# ---------------------------------------------------------------------------
# Live model fetching from provider APIs
# ---------------------------------------------------------------------------

# Provider API endpoints and auth patterns
_API_ENDPOINTS: dict[str, dict] = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/models?limit=100",
        "headers": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        "parse": "_parse_anthropic",
    },
    "openai": {
        "url": "https://api.openai.com/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_openai",
    },
    "openai-codex": {
        "url": "https://api.openai.com/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_openai",
    },
    "google": {
        "url_fn": lambda key: (
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            "&pageSize=100"
        ),
        "headers": lambda key: {},
        "parse": "_parse_google",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_openai",  # OpenAI-compatible
    },
    "deepseek": {
        "url": "https://api.deepseek.com/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_openai",  # OpenAI-compatible
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_mistral",
    },
    "together": {
        "url": "https://api.together.xyz/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_together",
    },
    "xai": {
        "url": "https://api.x.ai/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_openai",  # OpenAI-compatible
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "parse": "_parse_openrouter",
    },
}

# Model ID patterns to filter for chat-capable models per provider
_CHAT_MODEL_PATTERNS: dict[str, list[str]] = {
    "openai": ["gpt-4", "gpt-3.5", "o1", "o3", "o4"],
    "openai-codex": ["codex", "gpt-4", "gpt-5", "o1", "o3", "o4"],
}


def _parse_anthropic(data: dict) -> list[ModelOption]:
    """Parse Anthropic /v1/models response."""
    models = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        display = m.get("display_name", model_id)
        if not model_id or "claude" not in model_id:
            continue
        models.append(ModelOption(id=model_id, label=display, tier="api"))
    return sorted(models, key=lambda x: x.label)


def _parse_openai(data: dict) -> list[ModelOption]:
    """Parse OpenAI-compatible /v1/models response (also Groq, DeepSeek, xAI)."""
    models = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        if not model_id:
            continue
        # Skip embeddings, audio, image, moderation models
        skip_prefixes = (
            "text-embedding", "whisper", "tts", "dall-e", "davinci",
            "babbage", "curie", "ada", "ft:", "moderation",
        )
        if any(model_id.startswith(p) or model_id.startswith(f"o200k") for p in skip_prefixes):
            continue
        label = model_id.replace("-", " ").title()
        models.append(ModelOption(id=model_id, label=label, tier="api"))
    return sorted(models, key=lambda x: x.id)


def _parse_google(data: dict) -> list[ModelOption]:
    """Parse Google Gemini /v1beta/models response."""
    models = []
    for m in data.get("models", []):
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            continue
        name = m.get("name", "")
        model_id = name.replace("models/", "") if name.startswith("models/") else name
        display = m.get("displayName", model_id)
        if not model_id:
            continue
        models.append(ModelOption(id=model_id, label=display, tier="api"))
    return sorted(models, key=lambda x: x.label)


def _parse_mistral(data: dict | list) -> list[ModelOption]:
    """Parse Mistral /v1/models response (returns array or {data: [...]})."""
    items = data if isinstance(data, list) else data.get("data", [])
    models = []
    for m in items:
        model_id = m.get("id", "")
        if not model_id:
            continue
        caps = m.get("capabilities", {})
        if caps and not caps.get("completion_chat", True):
            continue
        label = model_id.replace("-", " ").title()
        models.append(ModelOption(id=model_id, label=label, tier="api"))
    return sorted(models, key=lambda x: x.id)


def _parse_together(data: dict | list) -> list[ModelOption]:
    """Parse Together /v1/models response. Filter to chat models."""
    items = data if isinstance(data, list) else data.get("data", [])
    models = []
    for m in items:
        model_id = m.get("id", "")
        model_type = m.get("type", "")
        if not model_id or model_type not in ("chat", "language"):
            continue
        display = m.get("display_name", model_id.split("/")[-1])
        models.append(ModelOption(id=model_id, label=display, tier="api"))
    return sorted(models, key=lambda x: x.label)


def _parse_openrouter(data: dict) -> list[ModelOption]:
    """Parse OpenRouter /api/v1/models response. Show top providers only."""
    models = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        display = m.get("name", model_id)
        if not model_id:
            continue
        models.append(ModelOption(id=model_id, label=display, tier="api"))
    return sorted(models, key=lambda x: x.label)


_PARSERS = {
    "_parse_anthropic": _parse_anthropic,
    "_parse_openai": _parse_openai,
    "_parse_google": _parse_google,
    "_parse_mistral": _parse_mistral,
    "_parse_together": _parse_together,
    "_parse_openrouter": _parse_openrouter,
}


def fetch_provider_models(
    provider: str,
    api_key: str,
    timeout: float = 3.0,
) -> list[ModelOption]:
    """Live-fetch available models from a provider's API.

    Returns a filtered list of chat-capable models, or an empty list on failure.
    For Ollama, use ``fetch_ollama_models()`` instead.
    """
    import json
    import urllib.error
    import urllib.request

    endpoint = _API_ENDPOINTS.get(provider)
    if not endpoint or not api_key:
        return []

    # Build URL (some providers embed the key in the URL)
    url_fn = endpoint.get("url_fn")
    url = url_fn(api_key) if url_fn else endpoint["url"]

    headers = endpoint["headers"](api_key)
    parse_fn_name = endpoint["parse"]
    parse_fn = _PARSERS.get(parse_fn_name)
    if parse_fn is None:
        # Fallback to OpenAI-compatible parser
        parse_fn = _parse_openai

    try:
        req = urllib.request.Request(url, method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return parse_fn(data)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        logger.debug("Failed to fetch models from %s: %s", provider, exc)
        return []


def fetch_ollama_models(timeout: float = 2.0) -> list[ModelOption]:
    """Live-fetch models from a running Ollama server.

    Falls back to an empty list if the server is unreachable.
    """
    import urllib.error
    import urllib.request

    url = "http://localhost:11434/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            import json

            data = json.loads(resp.read().decode())
            models = data.get("models", [])
            return [
                ModelOption(
                    id=m["name"],
                    label=m["name"],
                    tier="local",
                )
                for m in models
            ]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        logger.debug("Could not reach Ollama server at %s", url)
        return []
