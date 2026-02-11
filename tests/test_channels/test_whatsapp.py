"""Tests for the WhatsApp channel adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from vandelay.channels.whatsapp import WhatsAppAdapter


@pytest.fixture
def adapter():
    return WhatsAppAdapter(
        access_token="test-access-token",
        phone_number_id="123456789",
    )


class TestWhatsAppAdapterInit:
    def test_channel_name(self, adapter):
        assert adapter.channel_name == "whatsapp"

    def test_stores_config(self, adapter):
        assert adapter.access_token == "test-access-token"
        assert adapter.phone_number_id == "123456789"


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_is_noop(self, adapter):
        """start() should complete without error."""
        await adapter.start()

    @pytest.mark.asyncio
    async def test_stop_is_noop(self, adapter):
        """stop() should complete without error."""
        await adapter.stop()


class TestSend:
    @pytest.mark.asyncio
    async def test_send_delegates_to_whatsapp_tools(self, adapter):
        """send() should create WhatsAppTools and call send_text_message_async."""
        from vandelay.channels.base import OutgoingMessage

        msg = OutgoingMessage(
            text="Hello via WhatsApp!",
            session_id="wa:15551234567",
            channel="whatsapp",
        )

        with patch("agno.tools.whatsapp.WhatsAppTools") as mock_tools_cls:
            mock_tools = AsyncMock()
            mock_tools_cls.return_value = mock_tools

            await adapter.send(msg)

        mock_tools_cls.assert_called_once_with(
            access_token="test-access-token",
            phone_number_id="123456789",
            async_mode=True,
        )
        mock_tools.send_text_message_async.assert_called_once_with(
            text="Hello via WhatsApp!",
            recipient="15551234567",
        )

    @pytest.mark.asyncio
    async def test_send_no_recipient_warns(self, adapter):
        """send() with empty session_id should warn, not crash."""
        from vandelay.channels.base import OutgoingMessage

        msg = OutgoingMessage(text="test", session_id="wa:", channel="whatsapp")

        with patch("agno.tools.whatsapp.WhatsAppTools"):
            # Should not raise
            await adapter.send(msg)
