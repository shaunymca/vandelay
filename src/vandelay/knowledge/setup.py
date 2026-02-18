"""Knowledge setup — creates an Agno Knowledge instance backed by LanceDB or ChromaDB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vandelay.knowledge.embedder import create_embedder

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)


def create_knowledge(
    settings: Settings,
    db: Any = None,
    member_name: str | None = None,
) -> Any | None:
    """Build a Knowledge instance from settings.

    Args:
        settings: Application settings.
        db: Database backend for contents tracking (enables AgentOS playground UI).
        member_name: When provided, creates an isolated per-member collection
            named ``vandelay_knowledge_<member_name>``. When ``None``, uses the
            shared ``vandelay_knowledge`` collection.

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

    if member_name:
        slug = member_name.lower().replace(" ", "_").replace("-", "_")
        collection_name = f"vandelay_knowledge_{slug}"
        knowledge_name = f"vandelay-knowledge-{slug}"
    else:
        collection_name = "vandelay_knowledge"
        knowledge_name = "vandelay-knowledge"

    vector_db = create_vector_db(embedder, collection_name=collection_name)
    if vector_db is None:
        return None

    # Ensure knowledge directory exists
    knowledge_dir = Path(settings.workspace_dir) / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    return Knowledge(
        name=knowledge_name,
        vector_db=vector_db,
        contents_db=db,
    )
