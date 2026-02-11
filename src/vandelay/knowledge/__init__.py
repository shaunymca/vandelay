"""Knowledge/RAG subsystem."""

from vandelay.knowledge.embedder import create_embedder
from vandelay.knowledge.setup import create_knowledge

__all__ = ["create_embedder", "create_knowledge"]
