"""Status tab — live server metrics, memory count, uptime."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class StatusTab(Widget):
    """Live server status — polls /health and /status every 5 s."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="placeholder-outer"):
            yield Static("📊", classes="placeholder-icon")
            yield Label("Status", classes="placeholder-title")
            yield Label(
                "Agent name · Model · Uptime · Safety mode · Timezone\n"
                "Memory count · Total traces · Active channels",
                classes="placeholder-desc",
            )
