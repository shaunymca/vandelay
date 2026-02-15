"""Telegram channel adapter — polling (local) or webhooks (public URL)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

import httpx
from agno.media import Audio, File, Image, Video

from vandelay.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage
from vandelay.config.settings import get_settings

if TYPE_CHECKING:
    from vandelay.core.chat_service import ChatService

logger = logging.getLogger("vandelay.channels.telegram")

TELEGRAM_API = "https://api.telegram.org"


class TelegramAdapter(ChannelAdapter):
    """Telegram bot adapter with auto-detection: polling or webhooks.

    - No webhook_url configured → uses long-polling (works locally)
    - webhook_url configured → registers webhook with Telegram (needs public HTTPS)
    """

    channel_name = "telegram"

    def __init__(
        self,
        bot_token: str,
        chat_service: ChatService,
        chat_id: str = "",
        webhook_url: str = "",
        default_user_id: str = "",
    ) -> None:
        self.bot_token = bot_token
        self.chat_service = chat_service
        self.chat_id = chat_id
        self.webhook_url = webhook_url
        self.default_user_id = default_user_id
        self._bot_username: str | None = None
        self._polling_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Telegram adapter — polling or webhook mode."""
        # Fetch bot info
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{TELEGRAM_API}/bot{self.bot_token}/getMe")
                data = resp.json()
                if data.get("ok"):
                    self._bot_username = data["result"].get("username")
                    logger.info("Telegram bot: @%s", self._bot_username)
                else:
                    logger.error("Telegram getMe failed: %s", data)
                    return
        except Exception as exc:
            logger.error("Could not connect to Telegram: %s", exc)
            return

        if self.webhook_url:
            # Webhook mode — Telegram pushes updates to us
            await self._set_webhook(self.webhook_url)
            logger.info("Telegram running in webhook mode")
        else:
            # Polling mode — we pull updates from Telegram
            # First, remove any stale webhook
            await self._delete_webhook()
            self._stop_event.clear()
            self._polling_task = asyncio.create_task(
                self._poll_loop(), name="telegram-polling"
            )
            logger.info("Telegram running in polling mode")

    async def stop(self) -> None:
        """Stop the adapter — cancel polling or remove webhook."""
        if self._polling_task and not self._polling_task.done():
            self._stop_event.set()
            self._polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._polling_task
            self._polling_task = None
            logger.info("Telegram polling stopped")

        if self.webhook_url:
            await self._delete_webhook()

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Long-poll Telegram's getUpdates endpoint."""
        offset = 0
        timeout = 30  # seconds — Telegram long-poll timeout

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout + 10)) as client:
            while not self._stop_event.is_set():
                try:
                    resp = await client.get(
                        f"{TELEGRAM_API}/bot{self.bot_token}/getUpdates",
                        params={
                            "offset": offset,
                            "timeout": timeout,
                            "allowed_updates": '["message"]',
                        },
                    )
                    data = resp.json()

                    if not data.get("ok"):
                        logger.error("Telegram getUpdates error: %s", data)
                        await asyncio.sleep(5)
                        continue

                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        try:
                            await self.handle_update(update)
                        except Exception as exc:
                            logger.error(
                                "Error handling Telegram update: %s",
                                exc,
                                exc_info=True,
                            )

                except asyncio.CancelledError:
                    raise
                except httpx.ReadTimeout:
                    # Normal — long poll timed out with no updates
                    continue
                except Exception as exc:
                    logger.error("Telegram poll error: %s", exc)
                    await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # Outbound
    # ------------------------------------------------------------------

    async def send(self, message: OutgoingMessage) -> None:
        """Send a text message to a Telegram chat."""
        chat_id = message.session_id.removeprefix("tg:")
        if not chat_id:
            chat_id = self.chat_id
        if not chat_id:
            logger.warning("No chat_id for outbound Telegram message")
            return

        await self._send_text(chat_id, message.text)

    async def _send_text(self, chat_id: str, text: str) -> None:
        """Send text via Telegram Bot API (chunked at 4096 chars)."""
        max_len = 4096
        chunks = [text[i : i + max_len] for i in range(0, len(text), max_len)]

        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                try:
                    await client.post(
                        f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": chunk},
                    )
                except Exception as exc:
                    logger.error("Telegram send failed: %s", exc)

    async def _send_typing(self, chat_id: str) -> None:
        """Send 'typing...' chat action so the user knows we're working."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{TELEGRAM_API}/bot{self.bot_token}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                )
        except Exception as exc:
            logger.debug("Failed to send typing action: %s", exc)

    # ------------------------------------------------------------------
    # Inbound (called from webhook route or polling loop)
    # ------------------------------------------------------------------

    async def handle_update(self, update_data: dict[str, Any]) -> None:
        """Process a Telegram Update and respond."""
        message = update_data.get("message")
        if not message:
            return

        chat_id = str(message["chat"]["id"])
        user = message.get("from", {})
        tg_user_id = str(user.get("id", ""))
        session_id = f"tg:{chat_id}"

        # Auto-capture chat_id on first incoming message
        if not self.chat_id:
            self.chat_id = chat_id
            try:
                settings = get_settings()
                settings.channels.telegram_chat_id = chat_id
                settings.save()
                logger.info("Auto-captured Telegram chat_id: %s", chat_id)
            except Exception as exc:
                logger.warning("Failed to persist chat_id: %s", exc)

        # Use configured user_id for unified memory across channels
        user_id = self.default_user_id or tg_user_id

        # Extract text — could be message text or media caption
        text = message.get("text") or message.get("caption") or ""

        # Extract media attachments
        images: list[Image] = []
        audio_list: list[Audio] = []
        video_list: list[Video] = []
        files: list[File] = []

        if message.get("photo"):
            # Telegram sends multiple sizes; use the largest (last)
            photo = message["photo"][-1]
            data = await self._download_file(photo["file_id"])
            if data:
                images.append(Image(content=data))

        if message.get("audio"):
            data = await self._download_file(message["audio"]["file_id"])
            if data:
                audio_list.append(Audio(content=data))

        if message.get("voice"):
            data = await self._download_file(message["voice"]["file_id"])
            if data:
                audio_list.append(Audio(content=data))

        if message.get("video"):
            data = await self._download_file(message["video"]["file_id"])
            if data:
                video_list.append(Video(content=data))

        if message.get("document"):
            data = await self._download_file(message["document"]["file_id"])
            if data:
                files.append(File(content=data))

        # Drop updates that have neither text nor media
        if not text and not images and not audio_list and not video_list and not files:
            return

        # If media with no text, give the agent a hint
        if not text:
            media_types = []
            if images:
                media_types.append("image")
            if audio_list:
                media_types.append("audio")
            if video_list:
                media_types.append("video")
            if files:
                media_types.append("file")
            text = f"[User sent: {', '.join(media_types)}]"

        logger.info("Telegram message from %s in %s: %s", tg_user_id, chat_id, text[:80])

        incoming = IncomingMessage(
            text=text,
            session_id=session_id,
            user_id=user_id,
            channel="telegram",
            raw=update_data,
            images=images,
            audio=audio_list,
            video=video_list,
            files=files,
        )

        sent_any = False
        async for chunk in self.chat_service.run_chunked(
            incoming,
            typing=lambda: self._send_typing(chat_id),
        ):
            if chunk.error:
                await self._send_text(chat_id, f"Error: {chunk.error}")
                return
            if chunk.content:
                if sent_any:
                    await asyncio.sleep(0.4)  # natural pacing between chunks
                await self._send_text(chat_id, chunk.content)
                sent_any = True

        if not sent_any:
            await self._send_text(chat_id, "(no response)")

    # ------------------------------------------------------------------
    # File downloads
    # ------------------------------------------------------------------

    async def _download_file(self, file_id: str) -> bytes | None:
        """Download a file from Telegram by file_id. Returns raw bytes."""
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: resolve file_id → file_path
                resp = await client.post(
                    f"{TELEGRAM_API}/bot{self.bot_token}/getFile",
                    json={"file_id": file_id},
                )
                data = resp.json()
                if not data.get("ok"):
                    logger.warning("getFile failed for %s: %s", file_id, data)
                    return None

                file_path = data["result"].get("file_path")
                if not file_path:
                    return None

                # Step 2: download the actual file bytes
                download_url = f"{TELEGRAM_API}/file/bot{self.bot_token}/{file_path}"
                dl_resp = await client.get(download_url)
                dl_resp.raise_for_status()
                return dl_resp.content
        except Exception as exc:
            logger.error("Error downloading file %s: %s", file_id, exc)
        return None

    # ------------------------------------------------------------------
    # Webhook helpers
    # ------------------------------------------------------------------

    async def _set_webhook(self, url: str) -> None:
        """Register the webhook URL with Telegram."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{TELEGRAM_API}/bot{self.bot_token}/setWebhook",
                    json={"url": url},
                )
                result = resp.json()
                if result.get("ok"):
                    logger.info("Telegram webhook set to %s", url)
                else:
                    logger.error("Telegram setWebhook failed: %s", result)
        except Exception as exc:
            logger.error("Failed to set Telegram webhook: %s", exc)

    async def _delete_webhook(self) -> None:
        """Remove any existing webhook."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{TELEGRAM_API}/bot{self.bot_token}/deleteWebhook"
                )
                if resp.json().get("ok"):
                    logger.debug("Telegram webhook cleared")
        except Exception as exc:
            logger.warning("Failed to remove Telegram webhook: %s", exc)

    @property
    def bot_username(self) -> str | None:
        return self._bot_username

    @property
    def mode(self) -> str:
        """Current operating mode."""
        if self.webhook_url:
            return "webhook"
        if self._polling_task and not self._polling_task.done():
            return "polling"
        return "stopped"
