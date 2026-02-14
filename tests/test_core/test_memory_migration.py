"""Tests for memory migration from MEMORY.md to Agno native DB."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.core.memory_migration import (
    MEMORY_HEADER,
    MigrationResult,
    _content_to_memory_id,
    check_migration_needed,
    migrate_memory_to_db,
    parse_memory_entries,
)


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def test_settings(tmp_path: Path, workspace_dir: Path) -> Settings:
    return Settings(
        agent_name="TestAgent",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="trust"),
        workspace_dir=str(workspace_dir),
        user_id="test-user",
        enabled_tools=[],
        db_url="",
    )


class TestParseMemoryEntries:
    def test_empty_content(self):
        entries = parse_memory_entries("")
        assert entries == []

    def test_header_only(self):
        entries = parse_memory_entries(MEMORY_HEADER)
        assert entries == []

    def test_timestamped_entries(self):
        content = """# Memory

- [2026-02-14 10:45 UTC] User prefers dark mode
- [2026-02-15 09:00 UTC] Timezone is US/Pacific
"""
        entries = parse_memory_entries(content)
        assert len(entries) == 2
        assert entries[0].content == "User prefers dark mode"
        assert entries[0].timestamp == "2026-02-14 10:45 UTC"
        assert entries[1].content == "Timezone is US/Pacific"

    def test_plain_bullet_entries(self):
        content = """# Memory

- User prefers dark mode
- Always use uv for package management
"""
        entries = parse_memory_entries(content)
        assert len(entries) == 2
        assert entries[0].content == "User prefers dark mode"
        assert entries[0].timestamp is None

    def test_mixed_entries(self):
        content = """# Memory

- [2026-02-14 10:45 UTC] First entry with timestamp
- Plain entry without timestamp
"""
        entries = parse_memory_entries(content)
        assert len(entries) == 2
        assert entries[0].timestamp is not None
        assert entries[1].timestamp is None

    def test_section_headers_tracked(self):
        content = """# Memory

## Preferences
- User likes dark mode

## Technical
- Always use uv
"""
        entries = parse_memory_entries(content)
        assert len(entries) == 2
        assert entries[0].section == "Preferences"
        assert entries[0].content == "User likes dark mode"
        assert entries[1].section == "Technical"

    def test_prose_lines_skipped(self):
        content = """# Memory

Curated long-term memories. Update when something significant happens.

- Actual entry here
"""
        entries = parse_memory_entries(content)
        assert len(entries) == 1
        assert entries[0].content == "Actual entry here"


class TestContentToMemoryId:
    def test_deterministic(self):
        id1 = _content_to_memory_id("User prefers dark mode")
        id2 = _content_to_memory_id("User prefers dark mode")
        assert id1 == id2

    def test_case_insensitive(self):
        id1 = _content_to_memory_id("User prefers dark mode")
        id2 = _content_to_memory_id("user prefers dark mode")
        assert id1 == id2

    def test_strips_whitespace(self):
        id1 = _content_to_memory_id("User prefers dark mode")
        id2 = _content_to_memory_id("  User prefers dark mode  ")
        assert id1 == id2

    def test_different_content_different_ids(self):
        id1 = _content_to_memory_id("User prefers dark mode")
        id2 = _content_to_memory_id("User prefers light mode")
        assert id1 != id2

    def test_uuid_format(self):
        memory_id = _content_to_memory_id("test content")
        parts = memory_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestCheckMigrationNeeded:
    def test_no_memory_file(self, test_settings: Settings):
        assert check_migration_needed(test_settings) is False

    def test_header_only_file(self, test_settings: Settings, workspace_dir: Path):
        (workspace_dir / "MEMORY.md").write_text(MEMORY_HEADER, encoding="utf-8")
        assert check_migration_needed(test_settings) is False

    def test_file_with_entries(self, test_settings: Settings, workspace_dir: Path):
        content = MEMORY_HEADER + "\n- User prefers dark mode\n"
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")
        assert check_migration_needed(test_settings) is True


class TestMigrateMemoryToDb:
    def test_no_memory_file(self, test_settings: Settings):
        db = MagicMock()
        result = migrate_memory_to_db(test_settings, db=db)
        assert result.imported == 0
        db.upsert_memories.assert_not_called()

    def test_header_only(self, test_settings: Settings, workspace_dir: Path):
        (workspace_dir / "MEMORY.md").write_text(MEMORY_HEADER, encoding="utf-8")
        db = MagicMock()
        result = migrate_memory_to_db(test_settings, db=db)
        assert result.imported == 0
        db.upsert_memories.assert_not_called()

    def test_migrates_entries(self, test_settings: Settings, workspace_dir: Path):
        content = MEMORY_HEADER + "\n- User prefers dark mode\n- Timezone is UTC\n"
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")

        db = MagicMock()
        result = migrate_memory_to_db(test_settings, db=db)

        assert result.imported == 2
        db.upsert_memories.assert_called_once()
        memories = db.upsert_memories.call_args[0][0]
        assert len(memories) == 2
        assert memories[0].user_id == "test-user"
        assert memories[0].memory == "User prefers dark mode"
        assert memories[0].topics == ["imported_from_workspace"]

    def test_archives_original(self, test_settings: Settings, workspace_dir: Path):
        content = MEMORY_HEADER + "\n- Some entry\n"
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")

        db = MagicMock()
        result = migrate_memory_to_db(test_settings, db=db)

        backup = workspace_dir / "MEMORY.md.bak"
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == content
        assert result.archived == str(backup)

    def test_resets_memory_file(self, test_settings: Settings, workspace_dir: Path):
        content = MEMORY_HEADER + "\n- Some entry\n"
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")

        db = MagicMock()
        migrate_memory_to_db(test_settings, db=db)

        new_content = (workspace_dir / "MEMORY.md").read_text(encoding="utf-8")
        assert new_content == MEMORY_HEADER

    def test_idempotent_memory_ids(self, test_settings: Settings, workspace_dir: Path):
        """Re-running migration produces the same memory_ids (no duplicates)."""
        content = MEMORY_HEADER + "\n- Stable entry\n"
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")

        db = MagicMock()
        migrate_memory_to_db(test_settings, db=db)
        first_ids = [m.memory_id for m in db.upsert_memories.call_args[0][0]]

        # "Re-run" — write the same content back and migrate again
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")
        db.reset_mock()
        migrate_memory_to_db(test_settings, db=db)
        second_ids = [m.memory_id for m in db.upsert_memories.call_args[0][0]]

        assert first_ids == second_ids

    def test_section_prefix_in_memory(self, test_settings: Settings, workspace_dir: Path):
        content = "# Memory\n\n## Prefs\n- Dark mode preferred\n"
        (workspace_dir / "MEMORY.md").write_text(content, encoding="utf-8")

        db = MagicMock()
        migrate_memory_to_db(test_settings, db=db)

        memories = db.upsert_memories.call_args[0][0]
        assert memories[0].memory == "[Prefs] Dark mode preferred"
