"""WebSocket terminal channel adapter."""

from __future__ import annotations

from vandelay.channels.base import ChannelAdapter, OutgoingMessage


class WebSocketTerminalAdapter(ChannelAdapter):
    """Adapter for the /ws/terminal WebSocket endpoint.

    The WebSocket route handler manages its own connection lifecycle.
    This adapter exists for channel registry and routing purposes.
    """

    channel_name = "websocket"

    async def send(self, message: OutgoingMessage) -> None:
        # WebSocket messages are sent directly through the connection
        # in the route handler — this adapter is for registration only.
        raise NotImplementedError(
            "WebSocket messages are sent directly through the connection. "
            "Use the ws route handler instead."
        )

    async def start(self) -> None:
        # WebSocket connections are managed by FastAPI.
        pass
