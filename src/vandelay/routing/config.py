"""Router configuration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TierConfig(BaseModel):
    """Model configuration for a single complexity tier."""

    provider: str = ""
    model_id: str = ""


class RouterConfig(BaseModel):
    """LLM router settings — routes messages to different models by complexity.

    When ``enabled`` is True, each incoming message is classified into a tier
    (e.g. "simple" or "complex") and the agent's model is swapped accordingly.
    """

    enabled: bool = False
    tiers: dict[str, TierConfig] = Field(default_factory=lambda: {
        "simple": TierConfig(provider="anthropic", model_id="claude-haiku-4-5-20251001"),
        "complex": TierConfig(provider="anthropic", model_id="claude-sonnet-4-5-20250929"),
    })
