"""Database factory — creates the right Agno db backend from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agno.db.sqlite import SqliteDb

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

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
