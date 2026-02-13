"""Router middleware — swaps agent model based on message complexity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from vandelay.channels.base import IncomingMessage
from vandelay.core.agent_provider import AgentProvider
from vandelay.routing.classifier import classify

if TYPE_CHECKING:
    from vandelay.core.chat_service import ChatResponse
    from vandelay.routing.router import LLMRouter

logger = logging.getLogger("vandelay.routing.middleware")


class RouterMiddleware:
    """ChatMiddleware that classifies messages and swaps the agent model.

    Before each run, the message is classified into a tier and the agent's
    model is swapped to the tier-appropriate model. After the run, the
    original model is restored.

    Note: Not concurrency-safe — two simultaneous messages could race on
    model swap. Acceptable for now since Telegram and CLI are sequential.
    """

    def __init__(self, router: LLMRouter, agent_provider: AgentProvider) -> None:
        self._router = router
        self._get_agent = agent_provider
        self._original_model: Any | None = None

    async def before_run(self, message: IncomingMessage) -> None:
        """Classify message and swap agent model to the appropriate tier."""
        tier = classify(message.text)
        agent = self._get_agent()
        self._original_model = agent.model

        new_model = self._router.get_model_for_tier(tier)
        agent.model = new_model
        logger.debug("Routed to '%s' tier: %s", tier, getattr(new_model, "id", "?"))

    async def after_run(
        self, message: IncomingMessage, response: ChatResponse
    ) -> None:
        """Restore the original model after the run."""
        if self._original_model is not None:
            agent = self._get_agent()
            agent.model = self._original_model
            self._original_model = None
