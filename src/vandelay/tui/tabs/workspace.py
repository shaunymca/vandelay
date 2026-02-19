"""Workspace tab — file picker and embedded text editor."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class WorkspaceTab(Widget):
    """File picker + TextArea editor for workspace and member markdown files."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="placeholder-outer"):
            yield Static("📁", classes="placeholder-icon")
            yield Label("Workspace", classes="placeholder-title")
            yield Label(
                "SOUL.md · USER.md · AGENTS.md · TOOLS.md · HEARTBEAT.md\n"
                "Member files · Select file → edit in TextArea → Save",
                classes="placeholder-desc",
            )
