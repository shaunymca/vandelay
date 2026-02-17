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

    def test_has_send_file(self, toolkit):
        func_names = [f.name for f in toolkit.functions.values()]
        assert "send_file" in func_names


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

    @pytest.mark.asyncio
    async def test_unknown_channel_falls_back(self, router, adapter):
        router.register(adapter)
        toolkit = NotifyTools(channel_router=router)

        result = toolkit.notify_user("fallback test", channel="nonexistent")
        assert "sent via test" in result
        import asyncio
        await asyncio.sleep(0.01)
        assert len(adapter.sent) == 1

    @pytest.mark.asyncio
    async def test_notify_from_thread(self, router, adapter):
        """Verify notify_user works from a ThreadPoolExecutor (the Agno tool path)."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        router.register(adapter)
        toolkit = NotifyTools(channel_router=router)

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(
                pool, toolkit.notify_user, "from thread"
            )

        assert "sent via test" in result
        await asyncio.sleep(0.05)
        assert len(adapter.sent) == 1
        assert adapter.sent[0].text == "from thread"


class TestSendFile:
    @pytest.mark.asyncio
    async def test_send_file_success(self, router, adapter, tmp_path):
        router.register(adapter)
        toolkit = NotifyTools(channel_router=router)

        # Create a temp file to send
        test_file = tmp_path / "report.txt"
        test_file.write_text("hello world")

        result = toolkit.send_file(str(test_file), caption="Here's the report")

        assert "File sent via test" in result
        assert "report.txt" in result
        import asyncio
        await asyncio.sleep(0.01)
        assert len(adapter.sent) == 1
        msg = adapter.sent[0]
        assert msg.text == ""
        assert len(msg.attachments) == 1
        assert msg.attachments[0].path == str(test_file)
        assert msg.attachments[0].caption == "Here's the report"

    def test_send_file_not_found(self, router, adapter):
        router.register(adapter)
        toolkit = NotifyTools(channel_router=router)

        result = toolkit.send_file("/nonexistent/file.txt")
        assert "File not found" in result

    def test_send_file_no_channel(self, toolkit, tmp_path):
        test_file = tmp_path / "exists.txt"
        test_file.write_text("data")
        result = toolkit.send_file(str(test_file))
        assert "No active channels" in result
