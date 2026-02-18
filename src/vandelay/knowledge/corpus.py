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


@dataclass(frozen=True)
class RemoteCorpusSource:
    """A remote documentation URL that gets downloaded and section-filtered."""

    name: str
    url: str
    section_prefixes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LocalCorpusSource:
    """A file shipped in the ``vandelay.docs`` package."""

    name: str
    filename: str


CORPUS_SOURCES: list[RemoteCorpusSource | LocalCorpusSource] = [
    LocalCorpusSource("Vandelay Expert Reference", "VandelayExpert.txt"),
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
    """Parse ``llms-full.txt`` into pages and keep only matching ones.

    Pages start with ``# Title`` followed by ``Source: <url>`` on the next
    line.  We split on that pattern using regex, extract the URL, and keep
    pages whose URL path starts with any of the given *prefixes*.

    Returns a list of ``(source_url, page_text)`` tuples.
    """
    import re

    # Each page begins with "# Title\nSource: <url>".  We split just before
    # the "# " heading so each chunk contains exactly one page.
    parts = re.split(r"\n(?=# [^\n]+\nSource: )", text)
    total = 0
    kept: list[tuple[str, str]] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract Source: URL from the second line
        lines = part.splitlines()
        source_url = ""
        for line in lines[:5]:
            if line.startswith("Source:"):
                source_url = line[len("Source:"):].strip()
                break

        if not source_url:
            continue

        total += 1
        path = urlparse(source_url).path
        if any(path.startswith(prefix) for prefix in prefixes):
            kept.append((source_url, part))

    if not kept and total > 0:
        logger.warning(
            "Section filter matched 0 of %d pages — "
            "the llms-full.txt format may have changed",
            total,
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

    logger.info("Downloading corpus: %s (%s)", source.name, source.url)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(source.url)
        resp.raise_for_status()
        text = resp.text

    if not source.section_prefixes:
        # No filtering — index the whole document
        await knowledge.ainsert(text_content=text, name=source.name)
        return 1

    pages = parse_and_filter_sections(text, source.section_prefixes)
    if not pages:
        return 0

    count = 0
    for url, body in pages:
        page_name = f"{source.name}: {url}"
        await knowledge.ainsert(text_content=body, name=page_name)
        count += 1

    logger.info("Filtered %s — kept %d pages", source.name, count)
    return count


async def _index_local(
    knowledge: Any, source: LocalCorpusSource
) -> int:
    """Read a local doc from the ``vandelay.docs`` package and index it."""
    pkg = importlib.resources.files("vandelay.docs")
    text = (pkg / source.filename).read_text(encoding="utf-8")
    logger.info("Indexing local corpus: %s", source.name)
    await knowledge.ainsert(text_content=text, name=source.name)
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
