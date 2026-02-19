"""Agents tab — team members, enable/disable, edit prompt files."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class AgentsTab(Widget):
    """Team member manager — list, add, remove, edit .md prompt files."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="placeholder-outer"):
            yield Static("🤖", classes="placeholder-icon")
            yield Label("Agents", classes="placeholder-title")
            yield Label(
                "Team member list · Enable / Disable · Edit prompt files\n"
                "Add from 14 starter templates or start blank",
                classes="placeholder-desc",
            )
