"""Tests for the RouterMiddleware."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.channels.base import IncomingMessage
from vandelay.core.chat_service import ChatResponse
from vandelay.routing.middleware import RouterMiddleware


def _make_incoming(text: str = "hello") -> IncomingMessage:
    return IncomingMessage(text=text, session_id="test", channel="test")


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.model = MagicMock()
    agent.model.id = "original-model"
    return agent


@pytest.fixture
def mock_router():
    router = MagicMock()
    simple_model = MagicMock()
    simple_model.id = "haiku"
    complex_model = MagicMock()
    complex_model.id = "sonnet"
    router.get_model_for_tier.side_effect = lambda t: simple_model if t == "simple" else complex_model
    return router


class TestRouterMiddleware:
    @pytest.mark.asyncio
    async def test_swaps_model_before_run(self, mock_agent, mock_router):
        provider = lambda: mock_agent
        mw = RouterMiddleware(mock_router, provider)

        await mw.before_run(_make_incoming("hello"))

        # Model should have been swapped
        mock_router.get_model_for_tier.assert_called_once()
        assert mock_agent.model is not None

    @pytest.mark.asyncio
    async def test_restores_model_after_run(self, mock_agent, mock_router):
        original_model = mock_agent.model
        provider = lambda: mock_agent
        mw = RouterMiddleware(mock_router, provider)

        await mw.before_run(_make_incoming("hello"))
        assert mock_agent.model != original_model  # swapped

        await mw.after_run(_make_incoming("hello"), ChatResponse(content="ok"))
        assert mock_agent.model is original_model  # restored

    @pytest.mark.asyncio
    @patch("vandelay.routing.middleware.classify", return_value="simple")
    async def test_simple_message_uses_simple_tier(
        self, mock_classify, mock_agent, mock_router
    ):
        provider = lambda: mock_agent
        mw = RouterMiddleware(mock_router, provider)

        await mw.before_run(_make_incoming("hi"))
        mock_router.get_model_for_tier.assert_called_once_with("simple")

    @pytest.mark.asyncio
    @patch("vandelay.routing.middleware.classify", return_value="complex")
    async def test_complex_message_uses_complex_tier(
        self, mock_classify, mock_agent, mock_router
    ):
        provider = lambda: mock_agent
        mw = RouterMiddleware(mock_router, provider)

        await mw.before_run(_make_incoming("analyze this codebase"))
        mock_router.get_model_for_tier.assert_called_once_with("complex")

    @pytest.mark.asyncio
    async def test_after_run_without_before_is_safe(self, mock_agent, mock_router):
        """after_run should be safe to call even if before_run wasn't called."""
        provider = lambda: mock_agent
        mw = RouterMiddleware(mock_router, provider)

        # Should not raise
        await mw.after_run(_make_incoming(), ChatResponse(content="ok"))
