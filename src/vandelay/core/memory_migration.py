"""Migrate workspace MEMORY.md entries into Agno's native memory DB."""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from agno.memory import UserMemory

if TYPE_CHECKING:
    from agno.db.sqlite import SqliteDb

    from vandelay.config.settings import Settings

logger = logging.getLogger("vandelay.core.memory_migration")

# Header written to a freshly-reset MEMORY.md
MEMORY_HEADER = (
    "# Memory\n\nCurated long-term memories."
    " Update when something significant happens.\n"
)

# Matches timestamped entries: "- [2026-02-14 10:45 UTC] some text"
_TS_PATTERN = re.compile(
    r"^-\s*\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s*(?:UTC)?)\]\s*(.+)$"
)

# Matches plain bullet entries: "- some text"
_BULLET_PATTERN = re.compile(r"^-\s+(.+)$")

# Matches markdown section headers: "## Section Name"
_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")


@dataclass
class MemoryEntry:
    """A single parsed memory entry."""

    content: str
    timestamp: str | None = None
    section: str | None = None


@dataclass
class MigrationResult:
    """Result of a memory migration run."""

    imported: int = 0
    skipped: int = 0
    archived: str = ""
    entries: list[MemoryEntry] = field(default_factory=list)


def _content_to_memory_id(content: str) -> str:
    """Generate a deterministic UUID-like ID from content for idempotent upserts."""
    h = hashlib.sha256(content.strip().lower().encode("utf-8")).hexdigest()
    # Format as UUID: 8-4-4-4-12
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def parse_memory_entries(content: str) -> list[MemoryEntry]:
    """Parse MEMORY.md content into structured entries.

    Handles:
    - Timestamped lines: ``- [2026-02-14 10:45 UTC] User prefers dark mode``
    - Plain bullet lines: ``- User prefers dark mode``
    - Section headers: kept as context for subsequent entries

    Returns a list of MemoryEntry objects (headers alone are not entries).
    """
    entries: list[MemoryEntry] = []
    current_section: str | None = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # Check for section header (skip top-level h1 — it's the document title)
        header_match = _HEADER_PATTERN.match(line)
        if header_match:
            level = len(header_match.group(1))
            current_section = header_match.group(2).strip() if level >= 2 else None
            continue

        # Check for timestamped bullet
        ts_match = _TS_PATTERN.match(line)
        if ts_match:
            entries.append(
                MemoryEntry(
                    content=ts_match.group(2).strip(),
                    timestamp=ts_match.group(1).strip(),
                    section=current_section,
                )
            )
            continue

        # Check for plain bullet
        bullet_match = _BULLET_PATTERN.match(line)
        if bullet_match:
            entries.append(
                MemoryEntry(
                    content=bullet_match.group(1).strip(),
                    section=current_section,
                )
            )
            continue

        # Skip non-bullet prose (description text under headers, etc.)

    return entries


def _is_header_only(content: str) -> bool:
    """Check if the MEMORY.md content is just the header (no real entries)."""
    return len(parse_memory_entries(content)) == 0


def check_migration_needed(settings: Settings) -> bool:
    """Return True if MEMORY.md has entries that should be migrated.

    Migration is needed when:
    - MEMORY.md exists and has entries beyond the header
    """
    memory_path = Path(settings.workspace_dir) / "MEMORY.md"
    if not memory_path.exists():
        return False

    content = memory_path.read_text(encoding="utf-8")
    return not _is_header_only(content)


def migrate_memory_to_db(
    settings: Settings,
    db: SqliteDb | None = None,
) -> MigrationResult:
    """Migrate MEMORY.md entries into Agno's native memory DB.

    - Parses entries from MEMORY.md
    - Creates UserMemory objects with deterministic IDs (idempotent)
    - Bulk upserts into the database
    - Archives original file to MEMORY.md.bak
    - Resets MEMORY.md to just the header

    Args:
        settings: Application settings.
        db: Optional database instance. If not provided, creates one.

    Returns:
        MigrationResult with counts and archive path.
    """
    memory_path = Path(settings.workspace_dir) / "MEMORY.md"
    result = MigrationResult()

    if not memory_path.exists():
        logger.info("No MEMORY.md found — nothing to migrate.")
        return result

    content = memory_path.read_text(encoding="utf-8")
    entries = parse_memory_entries(content)

    if not entries:
        logger.info("MEMORY.md has no entries to migrate.")
        return result

    result.entries = entries

    # Create DB if not provided
    if db is None:
        from vandelay.memory.setup import create_db

        db = create_db(settings)

    # Build UserMemory objects
    user_id = settings.user_id or "default"
    memories: list[UserMemory] = []

    for entry in entries:
        memory_id = _content_to_memory_id(entry.content)
        memory_text = entry.content
        if entry.section:
            memory_text = f"[{entry.section}] {memory_text}"

        memories.append(
            UserMemory(
                memory_id=memory_id,
                user_id=user_id,
                memory=memory_text,
                topics=["imported_from_workspace"],
            )
        )

    # Bulk upsert
    db.upsert_memories(memories)
    result.imported = len(memories)
    logger.info("Imported %d memories into DB.", result.imported)

    # Archive original
    backup_path = memory_path.with_suffix(".md.bak")
    shutil.copy2(memory_path, backup_path)
    result.archived = str(backup_path)
    logger.info("Archived MEMORY.md to %s", backup_path)

    # Reset to header only
    memory_path.write_text(MEMORY_HEADER, encoding="utf-8")
    logger.info("Reset MEMORY.md to header.")

    return result
