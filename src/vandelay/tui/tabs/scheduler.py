"""Scheduler tab — Tasks and Cron jobs in sub-tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class SchedulerTab(Widget):
    """Cron + task manager — sub-tabs for Tasks and Cron jobs."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="placeholder-outer"):
            yield Static("🕐", classes="placeholder-icon")
            yield Label("Scheduler", classes="placeholder-title")
            yield Label(
                "Tasks: pending · running · done · failed  [Clear completed]\n"
                "Cron: add / edit / delete / enable / disable jobs",
                classes="placeholder-desc",
            )
