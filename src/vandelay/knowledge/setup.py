"""Knowledge setup — creates an Agno Knowledge instance backed by LanceDB or ChromaDB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
    except ImportError:
        logger.warning("agno knowledge package not available.")
        return None

    from vandelay.knowledge.vectordb import create_vector_db

    vector_db = create_vector_db(embedder)
    if vector_db is None:
        return None

    # Ensure knowledge directory exists
    knowledge_dir = Path(settings.workspace_dir) / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    return Knowledge(
        name="vandelay-knowledge",
        vector_db=vector_db,
        contents_db=db,
    )
