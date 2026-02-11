"""ASCII art banner for Vandelay."""

from rich.console import Console
from rich.text import Text

WORDMARK = """\
    ██╗   ██╗ █████╗ ███╗   ██╗██████╗ ███████╗██╗      █████╗ ██╗   ██╗
    ██║   ██║██╔══██╗████╗  ██║██╔══██╗██╔════╝██║     ██╔══██╗╚██╗ ██╔╝
    ██║   ██║███████║██╔██╗ ██║██║  ██║█████╗  ██║     ███████║ ╚████╔╝
    ╚██╗ ██╔╝██╔══██║██║╚██╗██║██║  ██║██╔══╝  ██║     ██╔══██║  ╚██╔╝
     ╚████╔╝ ██║  ██║██║ ╚████║██████╔╝███████╗███████╗██║  ██║   ██║
      ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝"""

TAGLINE = "The employee who doesn't exist."

# Compact version for narrower terminals
WORDMARK_COMPACT = """\
    __   __            _      _
    \\ \\ / /__ _ _ _  __| |___ | |__ _ _  _
     \\ V / _` | ' \\/ _` / -_)| / _` | || |
      \\_/\\__,_|_||_\\__,_\\___||_\\__,_|\\_, |
                                      |__/"""

# Smaller logomark for agent-ready screen
LOGO_SMALL = """\
    ╦  ╦╔═╗╔╗╔╔╦╗╔═╗╦  ╔═╗╦ ╦
    ╚╗╔╝╠═╣║║║ ║║║╣ ║  ╠═╣╚╦╝
     ╚╝ ╩ ╩╝╚╝═╩╝╚═╝╩═╝╩ ╩ ╩"""


def print_banner(console: Console, compact: bool = False) -> None:
    """Print the full Vandelay banner."""
    if compact:
        wm = Text(WORDMARK_COMPACT, style="bold red")
    else:
        width = console.width or 80
        if width < 85:
            wm = Text(WORDMARK_COMPACT, style="bold red")
        else:
            wm = Text(WORDMARK, style="bold red")

    console.print(wm, highlight=False)
    console.print(f"    [dim italic]{TAGLINE}[/dim italic]")
    console.print()


def print_agent_ready(console: Console, agent_name: str, version: str) -> None:
    """Print a compact startup banner when the agent loads."""
    logo_text = Text(LOGO_SMALL, style="bold red")
    console.print(logo_text, highlight=False)
    console.print(f"    [dim italic]{TAGLINE}[/dim italic]")
    console.print()
    console.print(f"  [bold red]{agent_name}[/bold red] [dim]v{version}[/dim]")
    console.print("  [dim]Type /help for commands[/dim]")
    console.print()
