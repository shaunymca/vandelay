"""Channel registry and router."""

from __future__ import annotations

from vandelay.channels.base import ChannelAdapter


class ChannelRouter:
    """Registry of active channel adapters."""

    def __init__(self) -> None:
        self._channels: dict[str, ChannelAdapter] = {}

    def register(self, adapter: ChannelAdapter) -> None:
        """Register a channel adapter."""
        self._channels[adapter.channel_name] = adapter

    def get(self, name: str) -> ChannelAdapter | None:
        """Retrieve a registered adapter by name."""
        return self._channels.get(name)

    @property
    def active_channels(self) -> list[str]:
        """List of registered channel names."""
        return list(self._channels.keys())

    async def start_all(self) -> None:
        """Start all registered channels."""
        for adapter in self._channels.values():
            await adapter.start()

    async def stop_all(self) -> None:
        """Stop all registered channels."""
        for adapter in self._channels.values():
            await adapter.stop()
