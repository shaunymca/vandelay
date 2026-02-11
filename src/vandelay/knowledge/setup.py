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


def create_knowledge(settings: Settings) -> Any | None:
    """Build a Knowledge instance from settings.

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

    vector_db = LanceDb(
        uri=str(VANDELAY_HOME / "data" / "knowledge_vectors"),
        table_name="vandelay_knowledge",
        embedder=embedder,
    )

    return Knowledge(
        name="vandelay-knowledge",
        vector_db=vector_db,
    )
