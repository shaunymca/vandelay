"""Tests for the NotifyTools agent toolkit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vandelay.channels.base import ChannelAdapter, OutgoingMessage
from vandelay.channels.router import ChannelRouter
from vandelay.tools.notify import NotifyTools


class FakeAdapter(ChannelAdapter):
    """In-memory channel adapter for testing."""

    channel_name = "test"

    def __init__(self):
        self.sent: list[OutgoingMessage] = []

    async def send(self, message: OutgoingMessage) -> None:
        self.sent.append(message)

    async def start(self) -> None:
        pass


@pytest.fixture
def router() -> ChannelRouter:
    return ChannelRouter()


@pytest.fixture
def adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def toolkit(router) -> NotifyTools:
    return NotifyTools(channel_router=router)


class TestNotifyToolsRegistration:
    def test_toolkit_name(self, toolkit):
        assert toolkit.name == "notify"

    def test_has_notify_user(self, toolkit):
        func_names = [f.name for f in toolkit.functions.values()]
        assert "notify_user" in func_names


class TestNotifyUser:
    def test_no_channels_returns_error(self, toolkit):
        result = toolkit.notify_user("hello")
        assert "No active channels" in result

    @pytest.mark.asyncio
    async def test_sends_to_first_available_channel(self, router, adapter):
        router.register(adapter)
        toolkit = NotifyTools(channel_router=router)

        result = toolkit.notify_user("Test alert")

        assert "sent via test" in result
        # Let the event loop process the task
        import asyncio
        await asyncio.sleep(0.01)
        assert len(adapter.sent) == 1
        assert adapter.sent[0].text == "Test alert"

    @pytest.mark.asyncio
    async def test_sends_to_named_channel(self, router):
        tg = FakeAdapter()
        tg.channel_name = "telegram"
        ws = FakeAdapter()
        ws.channel_name = "websocket"
        router.register(tg)
        router.register(ws)
        toolkit = NotifyTools(channel_router=router)

        result = toolkit.notify_user("TG only", channel="telegram")

        assert "sent via telegram" in result
        import asyncio
        await asyncio.sleep(0.01)
        assert len(tg.sent) == 1
        assert len(ws.sent) == 0

    def test_unknown_channel_falls_back(self, router, adapter):
        router.register(adapter)
        toolkit = NotifyTools(channel_router=router)

        result = toolkit.notify_user("fallback test", channel="nonexistent")
        assert "sent via test" in result
