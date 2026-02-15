"""Parse /thread and /threads commands from user messages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThreadCommand:
    """Result of parsing a potential thread command."""

    action: str  # "switch" | "show_current" | "list" | "none"
    thread_name: str = ""


def parse_thread_command(text: str) -> ThreadCommand:
    """Parse a message for thread commands.

    Returns a ThreadCommand with action="none" for normal messages.
    """
    stripped = text.strip()

    if stripped == "/threads":
        return ThreadCommand(action="list")

    if stripped == "/thread":
        return ThreadCommand(action="show_current")

    if stripped.startswith("/thread "):
        name = stripped[8:].strip()
        if not name:
            return ThreadCommand(action="show_current")
        return ThreadCommand(action="switch", thread_name=name)

    return ThreadCommand(action="none")
