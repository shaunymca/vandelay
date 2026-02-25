"""MainScreen — the primary TUI screen with all tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane

from vandelay.tui.tabs.agents import AgentsTab
from vandelay.tui.tabs.chat import ChatTab
from vandelay.tui.tabs.config import ConfigTab
from vandelay.tui.tabs.knowledge import KnowledgeTab
from vandelay.tui.tabs.memory import MemoryTab
from vandelay.tui.tabs.scheduler import SchedulerTab
from vandelay.tui.tabs.status import StatusTab
from vandelay.tui.tabs.workspace import WorkspaceTab
from vandelay.tui.widgets.header import VandelayHeader


class MainScreen(Screen):
    """Main screen: header + eight tabs."""

    def compose(self) -> ComposeResult:
        yield VandelayHeader()
        with TabbedContent(initial="tab-chat"):
            with TabPane("Chat", id="tab-chat"):
                yield ChatTab()
            with TabPane("Status", id="tab-status"):
                yield StatusTab()
            with TabPane("Config", id="tab-config"):
                yield ConfigTab()
            with TabPane("Agents", id="tab-agents"):
                yield AgentsTab()
            with TabPane("Scheduler", id="tab-scheduler"):
                yield SchedulerTab()
            with TabPane("Knowledge", id="tab-knowledge"):
                yield KnowledgeTab()
            with TabPane("Memory", id="tab-memory"):
                yield MemoryTab()
            with TabPane("Workspace", id="tab-workspace"):
                yield WorkspaceTab()

    def on_mount(self) -> None:
        from vandelay.config.settings import Settings

        if not Settings.config_exists():
            from vandelay.tui.screens.onboard_modal import FirstRunModal

            self.app.push_screen(FirstRunModal(), callback=self._on_first_run)

    def _on_first_run(self, result: str) -> None:
        if result == "skip":
            # User skipped onboarding — land on Config so they can set things up manually
            self.query_one(TabbedContent).active = "tab-config"
        # "done" → wizard completed, stay on Chat tab (already the default)
