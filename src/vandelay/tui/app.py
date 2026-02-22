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
    """Launch the TUI; handle any post-exit actions (e.g. onboarding)."""
    app = VandelayApp()
    result = app.run()

    if result == "onboard":
        from rich.console import Console

        from vandelay.cli.onboard import run_onboarding

        console = Console()
        try:
            settings = run_onboarding()
            console.print(
                f"\n[green]✓[/green] Setup complete — [bold]{settings.agent_name}[/bold] is ready.\n"  # noqa: E501
                "[dim]Run [bold]vandelay[/bold] to open the dashboard.[/dim]\n"
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled.[/yellow]\n")
