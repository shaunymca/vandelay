"""ASCII art banner for Vandelay."""

from rich.console import Console
from rich.text import Text

WORDMARK = """\
    ╦  ╦╔═╗╔╗╔╔╦╗╔═╗╦  ╔═╗╦ ╦
    ╚╗╔╝╠═╣║║║ ║║║╣ ║  ╠═╣╚╦╝
     ╚╝ ╩ ╩╝╚╝═╩╝╚═╝╩═╝╩ ╩ ╩"""

TAGLINE = "The employee who doesn't exist."


def print_banner(console: Console, compact: bool = False) -> None:
    """Print the full Vandelay banner."""
    wm = Text(WORDMARK, style="bold red")
    console.print(wm, highlight=False)
    console.print(f"    [dim italic]{TAGLINE}[/dim italic]")
    console.print()


def print_agent_ready(console: Console, agent_name: str, version: str) -> None:
    """Print a compact startup banner when the agent loads."""
    wm = Text(WORDMARK, style="bold red")
    console.print(wm, highlight=False)
    console.print(f"    [dim italic]{TAGLINE}[/dim italic]")
    console.print()
    console.print(f"  [bold red]{agent_name}[/bold red] [dim]v{version}[/dim]")
    console.print("  [dim]Type /help for commands[/dim]")
    console.print()
