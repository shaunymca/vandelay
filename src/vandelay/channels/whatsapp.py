"""WhatsApp channel adapter — thin wrapper around AgentOS Whatsapp interface."""

from __future__ import annotations

import logging

from vandelay.channels.base import ChannelAdapter, OutgoingMessage

logger = logging.getLogger("vandelay.channels.whatsapp")


class WhatsAppAdapter(ChannelAdapter):
    """Adapter for WhatsApp via AgentOS's built-in Whatsapp interface.

    The actual webhook handling, signature validation, and message routing
    are managed by AgentOS's ``Whatsapp`` interface. This adapter exists
    for channel registration and outbound message support.
    """

    channel_name = "whatsapp"

    def __init__(
        self,
        access_token: str = "",
        phone_number_id: str = "",
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id

    async def start(self) -> None:
        """No-op — AgentOS manages the WhatsApp webhook lifecycle."""
        logger.info("WhatsApp adapter registered (AgentOS handles webhooks)")

    async def stop(self) -> None:
        """No-op — AgentOS manages shutdown."""
        pass

    async def send(self, message: OutgoingMessage) -> None:
        """Send a text message via WhatsApp Business API."""
        try:
            from agno.tools.whatsapp import WhatsAppTools

            tools = WhatsAppTools(
                access_token=self.access_token,
                phone_number_id=self.phone_number_id,
                async_mode=True,
            )

            # Extract phone number from session_id (format: "wa:<phone>")
            recipient = message.session_id.removeprefix("wa:")
            if not recipient:
                logger.warning("No recipient for outbound WhatsApp message")
                return

            await tools.send_text_message_async(
                text=message.text,
                recipient=recipient,
            )
        except Exception as exc:
            logger.error("WhatsApp send failed: %s", exc, exc_info=True)
