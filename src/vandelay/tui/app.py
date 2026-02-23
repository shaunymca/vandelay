"""Vandelay TUI — main application entry point."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult

from vandelay.tui.screens.main import MainScreen


class VandelayApp(App[str | None]):
    """The Vandelay command centre TUI."""

    CSS_PATH = Path(__file__).parent / "theme.tcss"
    TITLE = "Vandelay"
    BINDINGS = [("quit", "Quit")]

    def compose(self) -> ComposeResult:
        # Nothing here — MainScreen owns all composition
        return iter([])

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def run_tui() -> None:
    """Launch the TUI."""
    app = VandelayApp()
    app.run()
