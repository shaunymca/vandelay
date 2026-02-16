"""Channel adapter interface for messaging transports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class IncomingMessage:
    """Normalized inbound message from any channel."""

    text: str
    session_id: str
    user_id: str | None = None
    channel: str = ""  # "websocket", "telegram", "whatsapp", etc.
    raw: dict | None = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)
    images: list = field(default_factory=list)  # List of agno.media.Image
    audio: list = field(default_factory=list)  # List of agno.media.Audio
    video: list = field(default_factory=list)  # List of agno.media.Video
    files: list = field(default_factory=list)  # List of agno.media.File


@dataclass
class Attachment:
    """A file attachment for outgoing messages."""

    path: str  # Absolute path on disk
    caption: str = ""  # Optional caption
    filename: str = ""  # Override display name (empty = basename)


@dataclass
class OutgoingMessage:
    """Normalized outbound message to any channel."""

    text: str
    session_id: str
    channel: str = ""
    attachments: list[Attachment] = field(default_factory=list)


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

    async def stop(self) -> None:  # noqa: B027
        """Graceful shutdown (optional override)."""
