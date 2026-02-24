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
    async def test_auto_capture_chat_id(self, mock_chat_service):
        """When chat_id is empty, it should be captured from the first message."""
        adapter = TelegramAdapter(
            bot_token="test-token-123",
            chat_service=mock_chat_service,
            chat_id="",  # empty — triggers auto-capture
        )
        update = {
            "message": {
                "text": "Hello",
                "chat": {"id": 55555},
                "from": {"id": 67890},
            }
        }

        with (
            patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls,
            patch("vandelay.channels.telegram.get_settings") as mock_get_settings,
        ):
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            mock_settings = MagicMock()
            mock_get_settings.return_value = mock_settings

            await adapter.handle_update(update)

        # chat_id should now be set on the adapter
        assert adapter.chat_id == "55555"
        # Settings should have been updated and saved
        assert mock_settings.channels.telegram_chat_id == "55555"
        mock_settings.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_re_capture_when_chat_id_set(self, adapter, mock_chat_service):
        """When chat_id is already set, it should NOT be re-captured."""
        update = {
            "message": {
                "text": "Hello",
                "chat": {"id": 99999},
                "from": {"id": 67890},
            }
        }

        with (
            patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls,
            patch(
                "vandelay.channels.telegram.get_settings"
            ) as mock_get_settings,
        ):
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.handle_update(update)

        # Should NOT have called get_settings since chat_id was already "12345"
        mock_get_settings.assert_not_called()
        assert adapter.chat_id == "12345"

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


class TestStart:
    """Regression tests for start() — polling must begin even if getMe fails."""

    @pytest.mark.asyncio
    async def test_start_polling_when_getme_fails_network(self, adapter):
        """Bug: if getMe raises a network error, polling was never started.
        Fix: start polling regardless; getMe failure is non-fatal."""
        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            # Simulate network failure on getMe and deleteWebhook
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

            await adapter.start()

        # Polling task should be created even though getMe failed
        assert adapter._polling_task is not None
        assert adapter.mode in ("polling", "stopped")  # task may have exited due to errors
        adapter._polling_task.cancel()

    @pytest.mark.asyncio
    async def test_start_polling_when_getme_returns_not_ok(self, adapter):
        """Bug: if getMe returns ok=false, start() returned early without starting polling."""
        import httpx as _httpx

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            bad_response = MagicMock()
            bad_response.json.return_value = {"ok": False, "description": "Unauthorized"}
            mock_client.get = AsyncMock(return_value=bad_response)

            ok_response = MagicMock()
            ok_response.json.return_value = {"ok": True}
            mock_client.post = AsyncMock(return_value=ok_response)

            await adapter.start()

        # Polling should still start; bot_username will be None
        assert adapter._polling_task is not None
        assert adapter._bot_username is None
        adapter._polling_task.cancel()

    @pytest.mark.asyncio
    async def test_start_polling_success(self, adapter):
        """Happy path: getMe succeeds, polling starts, mode is polling."""
        import httpx as _httpx

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            me_response = MagicMock()
            me_response.json.return_value = {"ok": True, "result": {"username": "mybot"}}
            mock_client.get = AsyncMock(return_value=me_response)

            webhook_response = MagicMock()
            webhook_response.json.return_value = {"ok": True}
            mock_client.post = AsyncMock(return_value=webhook_response)

            await adapter.start()

        assert adapter._bot_username == "mybot"
        assert adapter._polling_task is not None
        assert adapter.mode == "polling"
        adapter._polling_task.cancel()

    @pytest.mark.asyncio
    async def test_bot_username_after_successful_getme(self, adapter):
        """bot_username property should be set when getMe succeeds."""
        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            me_response = MagicMock()
            me_response.json.return_value = {"ok": True, "result": {"username": "vandelay_bot"}}
            mock_client.get = AsyncMock(return_value=me_response)

            webhook_response = MagicMock()
            webhook_response.json.return_value = {"ok": True}
            mock_client.post = AsyncMock(return_value=webhook_response)

            await adapter.start()

        assert adapter.bot_username == "vandelay_bot"
        adapter._polling_task.cancel()


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


class TestSendNotificationSessionId:
    @pytest.mark.asyncio
    async def test_notification_session_id_falls_back_to_stored_chat_id(self, adapter):
        """session_id='notification' (used by notify_user/send_file tools) must fall
        back to adapter.chat_id, not pass the literal string to Telegram."""
        from vandelay.channels.base import OutgoingMessage

        msg = OutgoingMessage(text="Hello!", session_id="notification", channel="telegram")

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["chat_id"] == "12345"  # adapter.chat_id

    @pytest.mark.asyncio
    async def test_tg_prefixed_session_id_uses_embedded_chat_id(self, adapter):
        """session_id='tg:99999' must use 99999, not fall back to stored chat_id."""
        from vandelay.channels.base import OutgoingMessage

        msg = OutgoingMessage(text="Hi", session_id="tg:99999", channel="telegram")

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["chat_id"] == "99999"


class TestSendDocument:
    @pytest.mark.asyncio
    async def test_send_document(self, adapter, tmp_path):
        """_send_document posts multipart to sendDocument endpoint."""
        test_file = tmp_path / "data.csv"
        test_file.write_text("a,b,c\n1,2,3")

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter._send_document("12345", str(test_file), caption="Report")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "sendDocument" in call_args[0][0]
        assert call_args[1]["data"]["chat_id"] == "12345"
        assert call_args[1]["data"]["caption"] == "Report"

    @pytest.mark.asyncio
    async def test_send_document_file_not_found(self, adapter):
        """_send_document logs error and returns if file doesn't exist."""
        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter._send_document("12345", "/nonexistent/file.txt")

        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_with_attachments_and_text(self, adapter, tmp_path):
        """send() dispatches both text and attachments."""
        from vandelay.channels.base import Attachment, OutgoingMessage

        test_file = tmp_path / "output.log"
        test_file.write_text("log data")

        msg = OutgoingMessage(
            text="Check this out",
            session_id="tg:12345",
            channel="telegram",
            attachments=[Attachment(path=str(test_file), caption="Logs")],
        )

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        # Should have at least 2 calls: sendMessage + sendDocument
        calls = mock_client.post.call_args_list
        urls = [c[0][0] for c in calls]
        assert any("sendMessage" in u for u in urls)
        assert any("sendDocument" in u for u in urls)


class TestSendPhoto:
    @pytest.mark.asyncio
    async def test_send_photo(self, adapter, tmp_path):
        """_send_photo posts multipart to sendPhoto endpoint."""
        img_file = tmp_path / "photo.jpg"
        img_file.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)  # minimal JPEG header

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter._send_photo("12345", str(img_file), caption="My photo")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "sendPhoto" in call_args[0][0]
        assert call_args[1]["data"]["chat_id"] == "12345"
        assert call_args[1]["data"]["caption"] == "My photo"

    @pytest.mark.asyncio
    async def test_send_photo_file_not_found(self, adapter):
        """_send_photo logs error and returns if file doesn't exist."""
        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter._send_photo("12345", "/nonexistent/photo.jpg")

        mock_client.post.assert_not_called()


class TestIsImage:
    def test_jpeg_is_image(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\x00")
        assert TelegramAdapter._is_image(str(f)) is True

    def test_jpeg_extension_is_image(self, tmp_path):
        f = tmp_path / "photo.jpeg"
        f.write_bytes(b"\x00")
        assert TelegramAdapter._is_image(str(f)) is True

    def test_png_is_image(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x00")
        assert TelegramAdapter._is_image(str(f)) is True

    def test_gif_is_image(self, tmp_path):
        f = tmp_path / "anim.gif"
        f.write_bytes(b"\x00")
        assert TelegramAdapter._is_image(str(f)) is True

    def test_webp_is_image(self, tmp_path):
        f = tmp_path / "modern.webp"
        f.write_bytes(b"\x00")
        assert TelegramAdapter._is_image(str(f)) is True

    def test_csv_not_image(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("a,b")
        assert TelegramAdapter._is_image(str(f)) is False

    def test_pdf_not_image(self, tmp_path):
        f = tmp_path / "report.pdf"
        f.write_bytes(b"%PDF")
        assert TelegramAdapter._is_image(str(f)) is False

    def test_log_not_image(self, tmp_path):
        f = tmp_path / "app.log"
        f.write_text("log")
        assert TelegramAdapter._is_image(str(f)) is False


class TestSendRoutesImageVsDocument:
    @pytest.mark.asyncio
    async def test_image_attachment_uses_send_photo(self, adapter, tmp_path):
        """Image attachments (.jpg) must use sendPhoto, not sendDocument."""
        from vandelay.channels.base import Attachment, OutgoingMessage

        img_file = tmp_path / "result.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 10)

        msg = OutgoingMessage(
            text="Here's your image",
            session_id="tg:12345",
            channel="telegram",
            attachments=[Attachment(path=str(img_file), caption="Chart")],
        )

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        calls = mock_client.post.call_args_list
        urls = [c[0][0] for c in calls]
        assert any("sendPhoto" in u for u in urls), f"Expected sendPhoto in {urls}"
        assert not any("sendDocument" in u for u in urls), f"sendDocument should not be used for images"

    @pytest.mark.asyncio
    async def test_non_image_attachment_uses_send_document(self, adapter, tmp_path):
        """Non-image attachments (.csv) must use sendDocument."""
        from vandelay.channels.base import Attachment, OutgoingMessage

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2")

        msg = OutgoingMessage(
            text="Here's the data",
            session_id="tg:12345",
            channel="telegram",
            attachments=[Attachment(path=str(csv_file), caption="Report")],
        )

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        calls = mock_client.post.call_args_list
        urls = [c[0][0] for c in calls]
        assert any("sendDocument" in u for u in urls), f"Expected sendDocument in {urls}"
        assert not any("sendPhoto" in u for u in urls), f"sendPhoto should not be used for non-images"

    @pytest.mark.asyncio
    async def test_mixed_attachments_routed_correctly(self, adapter, tmp_path):
        """Multiple attachments: images to sendPhoto, others to sendDocument."""
        from vandelay.channels.base import Attachment, OutgoingMessage

        img_file = tmp_path / "chart.jpg"
        img_file.write_bytes(b"\xff\xd8\xff")
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b")

        msg = OutgoingMessage(
            text="",
            session_id="tg:12345",
            channel="telegram",
            attachments=[
                Attachment(path=str(img_file)),
                Attachment(path=str(csv_file)),
            ],
        )

        with patch("vandelay.channels.telegram.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await adapter.send(msg)

        calls = mock_client.post.call_args_list
        urls = [c[0][0] for c in calls]
        assert any("sendPhoto" in u for u in urls)
        assert any("sendDocument" in u for u in urls)


class TestStripMarkdown:
    def test_headers(self):
        assert TelegramAdapter._strip_markdown("## Heading") == "Heading"
        assert TelegramAdapter._strip_markdown("# H1\n## H2") == "H1\nH2"

    def test_bold(self):
        assert TelegramAdapter._strip_markdown("**bold**") == "bold"

    def test_italic(self):
        assert TelegramAdapter._strip_markdown("*italic*") == "italic"

    def test_underscore_italic(self):
        assert TelegramAdapter._strip_markdown("_italic_") == "italic"

    def test_inline_code(self):
        assert TelegramAdapter._strip_markdown("`code`") == "code"

    def test_code_block(self):
        text = "```python\nprint('hi')\n```"
        result = TelegramAdapter._strip_markdown(text)
        assert "```" not in result
        assert "print('hi')" in result

    def test_links(self):
        result = TelegramAdapter._strip_markdown("[Google](https://google.com)")
        assert result == "Google (https://google.com)"

    def test_bullets(self):
        result = TelegramAdapter._strip_markdown("- item 1\n- item 2")
        assert result == "• item 1\n• item 2"

    def test_plain_text_unchanged(self):
        text = "Just some normal text with no markdown"
        assert TelegramAdapter._strip_markdown(text) == text

    def test_mixed_formatting(self):
        text = "## Status\n\n**Server**: running\n- CPU: 45%\n- Memory: `2.1GB`"
        result = TelegramAdapter._strip_markdown(text)
        assert "##" not in result
        assert "**" not in result
        assert "`" not in result
        assert "Status" in result
        assert "Server" in result
        assert "2.1GB" in result
