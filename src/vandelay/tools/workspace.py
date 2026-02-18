"""Agent-facing toolkit for reading and updating workspace markdown files."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from agno.tools import Toolkit

if TYPE_CHECKING:
    from agno.db.sqlite import SqliteDb

    from vandelay.config.settings import Settings

logger = logging.getLogger("vandelay.tools.workspace")

# Files the agent can write to (MEMORY.md is no longer writable — use update_memory() instead)
_WRITABLE_FILES = {"USER.md", "TOOLS.md"}

# Files the agent can read (superset of writable; MEMORY.md kept for backwards compat archive reads)
_READABLE_FILES = _WRITABLE_FILES | {"MEMORY.md", "SOUL.md", "AGENTS.md", "BOOTSTRAP.md", "HEARTBEAT.md"}


class WorkspaceTools(Toolkit):
    """Lets the agent read and update its workspace markdown files.

    Workspace files (USER.md, TOOLS.md) are injected into the system prompt on
    every restart. Long-term memories are stored in Agno's native memory DB via
    update_memory() — no longer written to MEMORY.md.
    """

    def __init__(self, settings: Settings, db: SqliteDb | None = None) -> None:
        super().__init__(name="workspace")
        self._workspace_dir = Path(settings.workspace_dir)
        self._db = db
        self._user_id = settings.user_id or "default"

        self.register(self.update_memory)
        self.register(self.update_user_profile)
        self.register(self.update_tools_notes)
        self.register(self.read_workspace_file)
        self.register(self.replace_workspace_file)

    def _resolve_path(self, name: str, allowed: set[str]) -> Path | None:
        """Resolve a workspace filename to a safe path, or None if disallowed."""
        # Strip any directory components — only bare filenames allowed
        clean = Path(name).name
        if clean not in allowed:
            return None
        return self._workspace_dir / clean

    def _append_entry(self, filename: str, entry: str) -> str:
        """Append a timestamped entry to a writable workspace file."""
        path = self._resolve_path(filename, _WRITABLE_FILES)
        if path is None:
            return f"Error: '{filename}' is not a writable workspace file."

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        line = f"\n- [{timestamp}] {entry}\n"

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

        logger.info("Appended to %s: %s", filename, entry[:80])
        return f"Appended to {filename}."

    def _write_memory_to_db(self, entry: str) -> str | None:
        """Try writing a memory entry to Agno's native DB.

        Returns a confirmation string on success, or None if DB is unavailable.
        """
        if self._db is None:
            return None

        try:
            from agno.memory import UserMemory

            from vandelay.core.memory_migration import _content_to_memory_id

            memory = UserMemory(
                memory_id=_content_to_memory_id(entry),
                user_id=self._user_id,
                memory=entry,
                topics=["workspace_memory"],
            )
            self._db.upsert_user_memory(memory)
            logger.info("Wrote memory to DB: %s", entry[:80])
            return f"Memory saved: {entry[:80]}"
        except Exception:
            logger.exception("Failed to write memory to DB")
            return None

    def update_memory(self, entry: str) -> str:
        """Save a long-term memory entry to the native memory database.

        Memories are stored in Agno's native DB and automatically retrieved
        on the next run — no file is written.

        Use this when you learn something important: user preferences,
        key decisions, lessons learned, or facts worth remembering.

        Args:
            entry: The text to save (one line, no markdown header needed).

        Returns:
            str: Confirmation message.
        """
        result = self._write_memory_to_db(entry)
        if result is not None:
            return result

        return (
            "Warning: native memory DB unavailable — memory not saved. "
            "Restart Vandelay to reinitialise the database."
        )

    def update_user_profile(self, entry: str) -> str:
        """Append a timestamped entry to USER.md — your profile of the user.

        Use this when you learn about the user: their name, role, projects,
        communication preferences, or working style.

        Args:
            entry: The text to append (one line, no markdown header needed).

        Returns:
            str: Confirmation message.
        """
        return self._append_entry("USER.md", entry)

    def update_tools_notes(self, entry: str) -> str:
        """Append a timestamped entry to TOOLS.md — your tool-specific notes.

        Use this when you discover useful tool patterns, configurations,
        or quirks worth remembering.

        Args:
            entry: The text to append (one line, no markdown header needed).

        Returns:
            str: Confirmation message.
        """
        return self._append_entry("TOOLS.md", entry)

    def read_workspace_file(self, name: str) -> str:
        """Read the contents of a workspace file.

        Available files: MEMORY.md, USER.md, TOOLS.md, SOUL.md, AGENTS.md,
        BOOTSTRAP.md, HEARTBEAT.md.

        Args:
            name: The filename to read (e.g. "MEMORY.md").

        Returns:
            str: The file contents, or an error message.
        """
        path = self._resolve_path(name, _READABLE_FILES)
        if path is None:
            allowed = ", ".join(sorted(_READABLE_FILES))
            return f"Error: '{name}' is not a valid workspace file. Allowed: {allowed}"

        if not path.exists():
            return f"{name} does not exist yet."

        return path.read_text(encoding="utf-8")

    def replace_workspace_file(self, name: str, content: str) -> str:
        """Replace the entire contents of a writable workspace file.

        Only USER.md and TOOLS.md can be replaced. Use this for curating and
        reorganizing — e.g. removing outdated entries.

        Args:
            name: The filename to replace (e.g. "USER.md").
            content: The new full content for the file.

        Returns:
            str: Confirmation message.
        """
        path = self._resolve_path(name, _WRITABLE_FILES)
        if path is None:
            allowed = ", ".join(sorted(_WRITABLE_FILES))
            return (
                f"Error: '{name}' is read-only or not a workspace file. "
                f"Writable files: {allowed}"
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        logger.info("Replaced %s (%d chars)", name, len(content))
        return f"Replaced {name} ({len(content)} chars)."
