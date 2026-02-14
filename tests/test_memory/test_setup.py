"""Tests for memory/setup — DB factory and stale session cleanup."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from agno.db.sqlite import SqliteDb

from vandelay.memory.setup import cleanup_stale_sessions


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary SqliteDb for testing."""
    db_file = str(tmp_path / "test.db")
    return SqliteDb(db_file=db_file)


def _insert_session(db: SqliteDb, session_id: str, user_id: str, session_type: str = "agent"):
    """Insert a raw session row for testing."""
    import time

    table = db._get_table(table_type="sessions", create_table_if_not_found=True)
    with db.Session() as sess, sess.begin():
        sess.execute(
            table.insert().values(
                session_id=session_id,
                session_type=session_type,
                user_id=user_id,
                agent_id="test-agent",
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )
        )


def _count_sessions(db: SqliteDb) -> int:
    """Count all rows in the sessions table."""
    from sqlalchemy import select, func

    table = db._get_table(table_type="sessions", create_table_if_not_found=True)
    with db.Session() as sess:
        result = sess.execute(select(func.count()).select_from(table))
        return result.scalar()


class TestCleanupStaleSessions:
    def test_deletes_sessions_with_wrong_user_id(self, tmp_db):
        _insert_session(tmp_db, "tg:123", "old-user-id")
        _insert_session(tmp_db, "tg:456", "old-user-id")
        assert _count_sessions(tmp_db) == 2

        deleted = cleanup_stale_sessions(tmp_db, "new-user@example.com")

        assert deleted == 2
        assert _count_sessions(tmp_db) == 0

    def test_keeps_sessions_with_matching_user_id(self, tmp_db):
        _insert_session(tmp_db, "tg:123", "correct@example.com")
        _insert_session(tmp_db, "tg:456", "wrong-user")

        deleted = cleanup_stale_sessions(tmp_db, "correct@example.com")

        assert deleted == 1
        assert _count_sessions(tmp_db) == 1

    def test_keeps_sessions_with_null_user_id(self, tmp_db):
        table = tmp_db._get_table(table_type="sessions", create_table_if_not_found=True)
        import time

        with tmp_db.Session() as sess, sess.begin():
            sess.execute(
                table.insert().values(
                    session_id="ws:anon",
                    session_type="agent",
                    user_id=None,
                    agent_id="test-agent",
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )
            )

        deleted = cleanup_stale_sessions(tmp_db, "user@example.com")

        assert deleted == 0
        assert _count_sessions(tmp_db) == 1

    def test_noop_when_no_sessions(self, tmp_db):
        deleted = cleanup_stale_sessions(tmp_db, "user@example.com")
        assert deleted == 0

    def test_noop_when_all_match(self, tmp_db):
        _insert_session(tmp_db, "tg:111", "user@example.com")
        _insert_session(tmp_db, "tg:222", "user@example.com")

        deleted = cleanup_stale_sessions(tmp_db, "user@example.com")

        assert deleted == 0
        assert _count_sessions(tmp_db) == 2
