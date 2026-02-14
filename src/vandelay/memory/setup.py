"""Database factory — creates the right Agno db backend from settings."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.db.sqlite import SqliteDb

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)

# Singleton cache — reuse the same SqliteDb instance per db path.
# Prevents SQLAlchemy MetaData conflicts when agents are recreated
# (Agno's SQLite backend is missing `extend_existing=True`).
_db_cache: dict[str, SqliteDb] = {}


def create_db(settings: Settings) -> SqliteDb:
    """Create or retrieve a cached database backend.

    Reuses the same SqliteDb instance for a given path to avoid
    the 'Table agno_memories is already defined' MetaData bug.
    """
    if settings.is_postgres:
        from agno.db.postgres import PostgresDb

        db_url = settings.db_url
        if db_url not in _db_cache:
            _db_cache[db_url] = PostgresDb(db_url=db_url)
        return _db_cache[db_url]

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(settings.db_path)

    if db_path_str not in _db_cache:
        _db_cache[db_path_str] = SqliteDb(db_file=db_path_str)

    return _db_cache[db_path_str]


def cleanup_stale_sessions(db: SqliteDb, user_id: str) -> int:
    """Delete sessions whose user_id doesn't match the current configured user_id.

    Agno's upsert_session silently drops writes when a session exists with the
    same session_id but a different user_id.  This leaves the agent unable to
    persist new sessions, causing context loss between messages.

    Call this once on startup, before creating agents or teams.

    Returns the number of deleted rows.
    """
    from sqlalchemy import delete as sa_delete

    table = db._get_table(table_type="sessions", create_table_if_not_found=True)
    if table is None:
        return 0

    try:
        with db.Session() as sess, sess.begin():
            stmt = (
                sa_delete(table)
                .where(table.c.user_id != user_id)
                .where(table.c.user_id.isnot(None))
            )
            result = sess.execute(stmt)
            count = result.rowcount
    except Exception:
        logger.exception("Failed to clean up stale sessions")
        return 0

    if count:
        logger.info(
            "Cleaned up %d stale session(s) with mismatched user_id "
            "(expected %r)",
            count,
            user_id,
        )
    return count
