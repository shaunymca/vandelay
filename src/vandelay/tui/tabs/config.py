"""Config tab — edit settings (model, tools, channels, safety, etc.)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class ConfigTab(Widget):
    """Settings editor — replaces `vandelay config` slash command."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="placeholder-outer"):
            yield Static("⚙️", classes="placeholder-icon")
            yield Label("Config", classes="placeholder-title")
            yield Label(
                "Agent · Model · Safety · Server · Tools · Channels\n"
                "Heartbeat · Team  —  Save to ~/.vandelay/config.json",
                classes="placeholder-desc",
            )
