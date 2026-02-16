"""Built-in documentation corpus for Vandelay Expert RAG."""

from __future__ import annotations

import json
import logging
from typing import Any

from vandelay.config.constants import CORPUS_VERSIONS_FILE

logger = logging.getLogger("vandelay.knowledge.corpus")

# Each entry is (human-readable name, URL).
CORPUS_URLS: list[tuple[str, str]] = [
    ("Agno Documentation", "https://docs.agno.com/llms-full.txt"),
]


def _get_current_versions() -> dict[str, str]:
    """Return installed package versions for cache-busting."""
    import agno

    import vandelay

    return {
        "agno": agno.__version__,
        "vandelay": vandelay.__version__,
    }


def _get_stored_versions() -> dict[str, str]:
    """Read version pins from disk; return ``{}`` if missing or corrupt."""
    try:
        return json.loads(CORPUS_VERSIONS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_versions(versions: dict[str, str]) -> None:
    """Persist version pins to disk."""
    CORPUS_VERSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_VERSIONS_FILE.write_text(
        json.dumps(versions, indent=2), encoding="utf-8"
    )


def corpus_needs_refresh() -> bool:
    """Return ``True`` when the corpus should be re-indexed."""
    return _get_current_versions() != _get_stored_versions()


async def index_corpus(knowledge: Any, *, force: bool = False) -> int:
    """Download and index all corpus URLs into *knowledge*.

    Returns the number of URLs successfully indexed.
    """
    if not force and not corpus_needs_refresh():
        return 0

    count = 0
    for name, url in CORPUS_URLS:
        try:
            logger.info("Indexing corpus: %s (%s)", name, url)
            await knowledge.ainsert(url=url, name=name)
            count += 1
        except Exception:
            logger.exception("Failed to index corpus URL: %s", url)

    _save_versions(_get_current_versions())
    return count
