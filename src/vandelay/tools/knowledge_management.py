"""KnowledgeManagementTools — lets agents manage per-member knowledge collections."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agno.tools import Toolkit, tool

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".docx", ".doc"}


class KnowledgeManagementTools(Toolkit):
    """Tools for managing per-member knowledge bases.

    Injected into the Vandelay Expert agent so it can add, inspect,
    and clear knowledge collections for any team member (or the shared base).
    """

    def __init__(self, settings: Settings, db: Any = None) -> None:
        self._settings = settings
        self._db = db
        super().__init__(name="knowledge_management")
        self.register(self.add_knowledge_document)
        self.register(self.list_knowledge)
        self.register(self.clear_knowledge)
        self.register(self.knowledge_status)

    def _get_knowledge(self, member_name: str):
        """Return a Knowledge instance for the given member (or shared if empty)."""
        from vandelay.knowledge.setup import create_knowledge

        name = member_name.strip() if member_name else None
        return create_knowledge(self._settings, db=self._db, member_name=name or None)

    @tool(description=(
        "Add a file or directory of documents to a team member's knowledge base. "
        "Pass member_name='' to add to the shared knowledge base. "
        "Supports .pdf, .txt, .md, .csv, .json, .docx, .doc files."
    ))
    def add_knowledge_document(self, file_path: str, member_name: str = "") -> str:
        """Load a file or directory into a knowledge collection.

        Args:
            file_path: Absolute or relative path to a file or directory.
            member_name: Team member name (e.g., 'cto', 'devops'). Empty = shared base.

        Returns:
            Summary of documents added.
        """
        target = Path(file_path).resolve()
        if not target.exists():
            return f"Path not found: {target}"

        # Collect files
        if target.is_file():
            if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
                return (
                    f"Unsupported file type: {target.suffix}. "
                    f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
                )
            files = [target]
        else:
            files = sorted(
                f for ext in SUPPORTED_EXTENSIONS for f in target.rglob(f"*{ext}")
            )

        if not files:
            return f"No supported files found under {target}"

        knowledge = self._get_knowledge(member_name)
        if knowledge is None:
            return (
                "Knowledge is not configured (disabled or no embedder). "
                "Check `vandelay knowledge status`."
            )

        from agno.knowledge.document import Document

        total = 0
        errors = []
        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
                knowledge.load(documents=[Document(name=fp.name, content=text)], upsert=True)
                total += 1
            except Exception as exc:
                errors.append(f"{fp.name}: {exc}")

        target_label = f"'{member_name}'" if member_name else "shared"
        result = f"Added {total} document(s) to {target_label} knowledge base."
        if errors:
            result += f" Errors: {'; '.join(errors)}"
        return result

    @tool(description=(
        "List the vector count for a team member's knowledge base. "
        "Pass member_name='' to check the shared knowledge base."
    ))
    def list_knowledge(self, member_name: str = "") -> str:
        """Show the number of vectors in a knowledge collection.

        Args:
            member_name: Team member name. Empty = shared base.

        Returns:
            Vector count and collection name.
        """
        knowledge = self._get_knowledge(member_name)
        if knowledge is None:
            return "Knowledge is not configured (disabled or no embedder)."

        from vandelay.knowledge.vectordb import get_vector_count

        count = get_vector_count(knowledge.vector_db)
        target_label = f"'{member_name}'" if member_name else "shared"
        return f"{target_label} knowledge base: {count} vector(s)."

    @tool(description=(
        "Clear (delete all vectors from) a team member's knowledge base. "
        "Pass member_name='' to clear the shared knowledge base. "
        "This is irreversible."
    ))
    def clear_knowledge(self, member_name: str = "") -> str:
        """Remove all vectors from a knowledge collection.

        Args:
            member_name: Team member name. Empty = shared base.

        Returns:
            Confirmation or error message.
        """
        knowledge = self._get_knowledge(member_name)
        if knowledge is None:
            return "Knowledge is not configured (disabled or no embedder)."

        target_label = f"'{member_name}'" if member_name else "shared"
        try:
            if hasattr(knowledge.vector_db, "drop"):
                knowledge.vector_db.drop()
                return f"Cleared {target_label} knowledge base."
            return f"Clear not supported for this vector DB backend."
        except Exception as exc:
            return f"Error clearing {target_label} knowledge base: {exc}"

    @tool(description=(
        "Show the status of all knowledge bases — shared plus one per team member. "
        "Lists collection names and vector counts."
    ))
    def knowledge_status(self, member_name: str = "") -> str:
        """Show knowledge status for a specific member or all members.

        Args:
            member_name: If provided, show only this member. Empty = show all.

        Returns:
            Status summary string.
        """
        from vandelay.knowledge.vectordb import get_vector_count

        lines = []

        def _check(label: str, mn: str | None) -> None:
            k = self._get_knowledge(mn or "")
            if k is None:
                lines.append(f"  {label}: unavailable")
                return
            count = get_vector_count(k.vector_db)
            lines.append(f"  {label}: {count} vector(s)")

        if member_name:
            _check(f"'{member_name}'", member_name)
        else:
            _check("shared", None)
            for entry in self._settings.team.members:
                name = entry if isinstance(entry, str) else entry.name
                _check(f"'{name}'", name)

        if not lines:
            return "No knowledge collections found."
        return "Knowledge status:\n" + "\n".join(lines)
