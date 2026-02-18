"""Vector DB factory — resolves ChromaDB or LanceDB based on availability."""

from __future__ import annotations

import logging
from typing import Any

from vandelay.config.constants import VANDELAY_HOME

logger = logging.getLogger(__name__)

_VECTOR_DIR = VANDELAY_HOME / "data" / "knowledge_vectors"
_DEFAULT_COLLECTION = "vandelay_knowledge"


def create_vector_db(
    embedder: Any,
    collection_name: str = _DEFAULT_COLLECTION,
) -> Any | None:
    """Create a vector DB instance, preferring ChromaDB with LanceDB fallback.

    Args:
        embedder: The embedder instance to use for vector creation.
        collection_name: ChromaDB collection / LanceDB table name.
            Defaults to ``"vandelay_knowledge"`` (the shared collection).
            Pass ``"vandelay_knowledge_<member>"`` for per-member isolation.

    Returns ``None`` if neither is available.
    """
    vdb = _try_chromadb(embedder, collection_name)
    if vdb is not None:
        return vdb

    vdb = _try_lancedb(embedder, collection_name)
    if vdb is not None:
        return vdb

    logger.warning(
        "No vector database available. "
        "Install chromadb (uv add chromadb) or lancedb (uv add lancedb)."
    )
    return None


def get_vector_count(vector_db: Any) -> int:
    """Get the number of vectors in a vector DB, handling both backends."""
    try:
        # LanceDB: table.count_rows()
        if hasattr(vector_db, "table") and vector_db.table is not None:
            return vector_db.table.count_rows()
        if hasattr(vector_db, "_table") and vector_db._table is not None:
            return vector_db._table.count_rows()
        # ChromaDB: _collection.count()
        if hasattr(vector_db, "_collection") and vector_db._collection is not None:
            return vector_db._collection.count()
        if hasattr(vector_db, "collection") and vector_db.collection is not None:
            return vector_db.collection.count()
    except Exception:
        pass
    return 0


def _try_lancedb(embedder: Any, collection_name: str = _DEFAULT_COLLECTION) -> Any | None:
    try:
        from agno.vectordb.lancedb import LanceDb
    except ImportError:
        return None

    import os

    # Suppress noisy Lance Rust WARN on stderr during first-run table creation
    _devnull = os.open(os.devnull, os.O_WRONLY)
    _prev_stderr_fd = os.dup(2)
    os.dup2(_devnull, 2)
    os.close(_devnull)
    try:
        return LanceDb(
            uri=str(_VECTOR_DIR),
            table_name=collection_name,
            embedder=embedder,
        )
    except Exception as exc:
        logger.debug("LanceDB init failed: %s", exc)
        return None
    finally:
        os.dup2(_prev_stderr_fd, 2)
        os.close(_prev_stderr_fd)


def _try_chromadb(embedder: Any, collection_name: str = _DEFAULT_COLLECTION) -> Any | None:
    try:
        from agno.vectordb.chroma import ChromaDb
    except ImportError:
        return None

    _VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    try:
        return ChromaDb(
            path=str(_VECTOR_DIR),
            collection=collection_name,
            persistent_client=True,
            embedder=embedder,
        )
    except Exception as exc:
        logger.debug("ChromaDB init failed: %s", exc)
        return None
