"""Agent-facing toolkit for proactive user notifications."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from agno.tools import Toolkit

if TYPE_CHECKING:
    from vandelay.channels.router import ChannelRouter

logger = logging.getLogger("vandelay.tools.notify")


class NotifyTools(Toolkit):
    """Lets the agent send proactive messages to the user via any active channel."""

    def __init__(self, channel_router: ChannelRouter) -> None:
        super().__init__(name="notify")
        self._router = channel_router
        self.register(self.notify_user)

    def notify_user(self, message: str, channel: str = "") -> str:
        """Send a proactive notification to the user.

        Use this when you need to alert the user about something important
        outside a normal conversation turn — for example, a completed cron job,
        a heartbeat alert, a reminder, or a scheduled task result.

        Args:
            message: The notification text to send.
            channel: Target channel name (e.g. "telegram"). If empty, sends to
                the first available channel.

        Returns:
            Confirmation string or error description.
        """
        from vandelay.channels.base import OutgoingMessage

        adapter = self._router.get(channel) if channel else None
        if adapter is None:
            channels = self._router.active_channels
            if channels:
                adapter = self._router.get(channels[0])

        if adapter is None:
            logger.warning("notify_user called but no channels available")
            return "No active channels — notification could not be delivered."

        try:
            asyncio.get_event_loop().create_task(
                adapter.send(OutgoingMessage(
                    text=message,
                    session_id="notification",
                    channel=adapter.channel_name,
                ))
            )
            return f"Notification sent via {adapter.channel_name}."
        except Exception as exc:
            logger.warning("Failed to send notification: %s", exc)
            return f"Failed to send notification: {exc}"
