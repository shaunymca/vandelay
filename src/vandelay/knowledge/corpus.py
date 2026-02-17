"""Built-in documentation corpus for Vandelay Expert RAG."""

from __future__ import annotations

import importlib.resources
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from vandelay.config.constants import CORPUS_VERSIONS_FILE

logger = logging.getLogger("vandelay.knowledge.corpus")

# URL path prefixes to keep from Agno llms-full.txt
AGNO_SECTION_PREFIXES: list[str] = [
    "/tools/",
    "/agents/",
    "/teams/",
    "/memory/",
    "/knowledge/",
    "/context/",
    "/basics/",
]


@dataclass(frozen=True)
class RemoteCorpusSource:
    """A remote documentation URL that gets downloaded and section-filtered."""

    name: str
    url: str
    section_prefixes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LocalCorpusSource:
    """A markdown file shipped in the ``vandelay.docs`` package."""

    name: str
    filename: str


CORPUS_SOURCES: list[RemoteCorpusSource | LocalCorpusSource] = [
    RemoteCorpusSource(
        "Agno Documentation",
        "https://docs.agno.com/llms-full.txt",
        AGNO_SECTION_PREFIXES,
    ),
    LocalCorpusSource("Vandelay Config Reference", "CONFIG.md"),
    LocalCorpusSource("Vandelay Operations Guide", "OPERATIONS.md"),
]

# Backward compat — existing code may import CORPUS_URLS
CORPUS_URLS: list[tuple[str, str]] = [
    (s.name, s.url) for s in CORPUS_SOURCES if isinstance(s, RemoteCorpusSource)
]


# ---------------------------------------------------------------------------
# Section parser for llms-full.txt format
# ---------------------------------------------------------------------------


def parse_and_filter_sections(
    text: str, prefixes: list[str]
) -> list[tuple[str, str]]:
    """Parse ``llms-full.txt`` into sections and keep only matching ones.

    Each section is separated by ``---`` on its own line. The first few lines
    contain ``Source: <url>`` which we match against *prefixes*.

    Returns a list of ``(source_url, section_text)`` tuples.
    """
    raw_sections = text.split("\n---\n")
    kept: list[tuple[str, str]] = []

    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        # Extract Source: URL from the section header
        source_url = ""
        for line in section.splitlines()[:10]:
            if line.startswith("Source:"):
                source_url = line[len("Source:"):].strip()
                break

        if not source_url:
            continue

        path = urlparse(source_url).path
        if any(path.startswith(prefix) for prefix in prefixes):
            kept.append((source_url, section))

    if not kept:
        logger.warning(
            "Section filter matched 0 of %d sections — "
            "the llms-full.txt format may have changed",
            len(raw_sections),
        )

    return kept


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


async def _index_remote(
    knowledge: Any, source: RemoteCorpusSource
) -> int:
    """Download, parse, filter, and index a remote corpus source."""
    import httpx
    from agno.knowledge.document import Document

    logger.info("Downloading corpus: %s (%s)", source.name, source.url)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(source.url)
        resp.raise_for_status()
        text = resp.text

    if not source.section_prefixes:
        # No filtering — index the whole document
        doc = Document(name=source.name, content=text)
        await knowledge.ainsert(documents=[doc])
        return 1

    sections = parse_and_filter_sections(text, source.section_prefixes)
    if not sections:
        return 0

    docs = [
        Document(name=f"{source.name}: {url}", content=body)
        for url, body in sections
    ]
    logger.info(
        "Filtered %d sections from %s (kept %d)",
        len(text.split("\n---\n")),
        source.name,
        len(docs),
    )
    await knowledge.ainsert(documents=docs)
    return len(docs)


async def _index_local(
    knowledge: Any, source: LocalCorpusSource
) -> int:
    """Read a local doc from the ``vandelay.docs`` package and index it."""
    from agno.knowledge.document import Document

    pkg = importlib.resources.files("vandelay.docs")
    text = (pkg / source.filename).read_text(encoding="utf-8")
    doc = Document(name=source.name, content=text)
    logger.info("Indexing local corpus: %s", source.name)
    await knowledge.ainsert(documents=[doc])
    return 1


async def index_corpus(knowledge: Any, *, force: bool = False) -> int:
    """Download and index all corpus sources into *knowledge*.

    Returns the number of sources successfully indexed.
    """
    if not force and not corpus_needs_refresh():
        return 0

    count = 0
    for source in CORPUS_SOURCES:
        try:
            if isinstance(source, RemoteCorpusSource):
                count += await _index_remote(knowledge, source)
            elif isinstance(source, LocalCorpusSource):
                count += await _index_local(knowledge, source)
        except Exception:
            logger.exception("Failed to index corpus source: %s", source.name)

    _save_versions(_get_current_versions())
    return count
