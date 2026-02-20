"""Chat tab — real-time chat with the agent via WebSocket."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class ChatTab(Widget):
    """Chat interface — connects to /ws/terminal when server is online."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="placeholder-outer"):
            yield Static("💬", classes="placeholder-icon")
            yield Label("Chat", classes="placeholder-title")
            yield Label(
                "Real-time chat with your agent.\n"
                "Streaming responses, tool call indicators, /new to reset session.",
                classes="placeholder-desc",
            )
