"""Tests for the Telegram channel adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vandelay.channels.telegram import TelegramAdapter
from vandelay.core.chat_service import ChatResponse, ChatService


async def _async_gen(*items):
    for item in items:
        yield item


@pytest.fixture
def mock_chat_service():
    svc = MagicMock(spec=ChatService)
    svc.run = AsyncMock(return_value=ChatResponse(content="Hello from the agent!"))
    svc.run_chunked = MagicMock(
        return_value=_async_gen(ChatResponse(content="Hello from the agent!"))
    )
    return svc


@pytest.fixture
def adapter(mock_chat_service):
    return TelegramAdapter(
        bot_token="test-token-123",
        chat_service=mock_chat_service,
        chat_id="12345",
    )


class TestTelegramAdapterInit:
    def test_channel_name(self, adapter):
        assert adapter.channel_name == "telegram"

    def test_stores_config(self, adapter):
        assert adapter.bot_token == "test-token-123"
        assert adapter.chat_id == "12345"


class TestHandleUpdate:
    @pytest.mark.asyncio
    async def test_text_message(self, adapter, mock_chat_service):
        """A standard text message should invoke chat_service.run and reply."""
        update = {
            "message": {
                "text": "Hello bot",
                "chat": {"id": 12345},
                "from": {"id": 67890, "first_name": "Test"},
            }
        }

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.handle_update(update)

        mock_chat_service.run_chunked.assert_called_once()
        call_args = mock_chat_service.run_chunked.call_args
        incoming = call_args[0][0]
        assert incoming.text == "Hello bot"
        assert incoming.user_id == "67890"
        assert incoming.session_id == "tg:12345"
        assert incoming.channel == "telegram"

    @pytest.mark.asyncio
    async def test_non_message_update_ignored(self, adapter, mock_chat_service):
        """Updates without a 'message' key (e.g. edited_message) are skipped."""
        update = {"edited_message": {"text": "edited"}}
        await adapter.handle_update(update)
        mock_chat_service.run_chunked.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_text_message_ignored(self, adapter, mock_chat_service):
        """Messages without text (photos, stickers) are skipped."""
        update = {
            "message": {
                "chat": {"id": 12345},
                "from": {"id": 67890},
                "photo": [{"file_id": "abc"}],
            }
        }
        await adapter.handle_update(update)
        mock_chat_service.run_chunked.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_text_ignored(self, adapter, mock_chat_service):
        """Messages with empty text are skipped."""
        update = {
            "message": {
                "text": "",
                "chat": {"id": 12345},
                "from": {"id": 67890},
            }
        }
        await adapter.handle_update(update)
        mock_chat_service.run_chunked.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_response_sends_error(self, adapter, mock_chat_service):
        """When chat_service returns an error, it's sent as 'Error: ...'."""
        mock_chat_service.run_chunked = MagicMock(
            return_value=_async_gen(ChatResponse(error="Something broke"))
        )
        update = {
            "message": {
                "text": "Hello",
                "chat": {"id": 12345},
                "from": {"id": 67890},
            }
        }

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.handle_update(update)

        # Should have sent typing + error message
        calls = mock_client.post.call_args_list
        send_calls = [c for c in calls if "sendMessage" in str(c)]
        assert len(send_calls) == 1
        assert "Error: Something broke" in str(send_calls[0])


class TestMode:
    def test_default_mode_is_stopped(self, adapter):
        assert adapter.mode == "stopped"

    def test_webhook_mode(self, adapter):
        adapter.webhook_url = "https://example.com/telegram/webhook"
        assert adapter.mode == "webhook"


class TestSend:
    @pytest.mark.asyncio
    async def test_send_uses_session_id(self, adapter):
        """Outbound send extracts chat_id from session_id."""
        from vandelay.channels.base import OutgoingMessage

        msg = OutgoingMessage(text="Hi!", session_id="tg:99999", channel="telegram")

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["chat_id"] == "99999"
        assert call_args[1]["json"]["text"] == "Hi!"
