"""Knowledge setup — creates an Agno Knowledge instance backed by LanceDB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vandelay.config.constants import VANDELAY_HOME
from vandelay.knowledge.embedder import create_embedder

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)


def create_knowledge(settings: Settings, db: Any = None) -> Any | None:
    """Build a Knowledge instance from settings.

    Args:
        settings: Application settings.
        db: Database backend for contents tracking (enables AgentOS playground UI).

    Returns ``None`` when knowledge is disabled or no embedder is available.
    The caller should pass ``None`` safely — the Agent works fine without it.
    """
    if not settings.knowledge.enabled:
        return None

    embedder = create_embedder(settings)
    if embedder is None:
        return None

    try:
        from agno.knowledge.knowledge import Knowledge
        from agno.vectordb.lancedb import LanceDb
    except ImportError:
        logger.warning(
            "lancedb or agno knowledge packages not installed. "
            "Run: uv add lancedb"
        )
        return None

    # Ensure knowledge directory exists
    knowledge_dir = Path(settings.workspace_dir) / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # Suppress noisy INFO/WARN from agno and lance during first-run table creation
    # (e.g. "Creating table: vandelay_knowledge", "No existing dataset ...")
    import os
    import sys

    _agno_logger = logging.getLogger("agno")
    _prev_agno = _agno_logger.level
    _agno_logger.setLevel(logging.ERROR)

    # Lance Rust WARN writes directly to the OS stderr fd, bypassing Python's
    # sys.stderr. We must redirect at the file-descriptor level to catch it.
    _devnull = os.open(os.devnull, os.O_WRONLY)
    _prev_stderr_fd = os.dup(2)
    os.dup2(_devnull, 2)
    os.close(_devnull)

    try:
        vector_db = LanceDb(
            uri=str(VANDELAY_HOME / "data" / "knowledge_vectors"),
            table_name="vandelay_knowledge",
            embedder=embedder,
        )

        return Knowledge(
            name="vandelay-knowledge",
            vector_db=vector_db,
            contents_db=db,
        )
    finally:
        os.dup2(_prev_stderr_fd, 2)
        os.close(_prev_stderr_fd)
        _agno_logger.setLevel(_prev_agno)
