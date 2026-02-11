"""Channel adapter interface for messaging transports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IncomingMessage:
    """Normalized inbound message from any channel."""

    text: str
    session_id: str
    user_id: Optional[str] = None
    channel: str = ""  # "websocket", "telegram", "whatsapp", etc.
    raw: Optional[dict] = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    """Normalized outbound message to any channel."""

    text: str
    session_id: str
    channel: str = ""


class ChannelAdapter(ABC):
    """Base class for all message channel adapters.

    Translates between a channel's native protocol and the
    normalized IncomingMessage/OutgoingMessage format.
    """

    channel_name: str = ""

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> None:
        """Send a message through this channel."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start listening for incoming messages (if applicable)."""
        ...

    async def stop(self) -> None:
        """Graceful shutdown (optional override)."""
        pass
