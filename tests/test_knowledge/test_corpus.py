"""Tests for the built-in documentation corpus."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vandelay.knowledge.corpus import (
    CORPUS_SOURCES,
    CORPUS_URLS,
    LocalCorpusSource,
    RemoteCorpusSource,
    _get_current_versions,
    _get_stored_versions,
    _save_versions,
    corpus_needs_refresh,
    index_corpus,
    parse_and_filter_sections,
)


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


def test_get_current_versions():
    import agno

    import vandelay

    result = _get_current_versions()
    assert result == {"agno": agno.__version__, "vandelay": vandelay.__version__}


def test_stored_versions_missing_file(tmp_path):
    fake_path = tmp_path / "nope.json"
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", fake_path):
        assert _get_stored_versions() == {}


def test_stored_versions_corrupt_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json!", encoding="utf-8")
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", bad_file):
        assert _get_stored_versions() == {}


def test_save_and_load_roundtrip(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    versions = {"agno": "1.0.0", "vandelay": "0.2.0"}
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        _save_versions(versions)
        assert _get_stored_versions() == versions


# ---------------------------------------------------------------------------
# corpus_needs_refresh
# ---------------------------------------------------------------------------


def test_corpus_needs_refresh_no_file(tmp_path):
    fake_path = tmp_path / "nope.json"
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", fake_path):
        assert corpus_needs_refresh() is True


def test_corpus_needs_refresh_matching(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        current = _get_current_versions()
        _save_versions(current)
        assert corpus_needs_refresh() is False


def test_corpus_needs_refresh_agno_changed(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        current = _get_current_versions()
        current["agno"] = "0.0.0-old"
        _save_versions(current)
        assert corpus_needs_refresh() is True


def test_corpus_needs_refresh_vandelay_changed(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        current = _get_current_versions()
        current["vandelay"] = "0.0.0-old"
        _save_versions(current)
        assert corpus_needs_refresh() is True


# ---------------------------------------------------------------------------
# parse_and_filter_sections
# ---------------------------------------------------------------------------

SAMPLE_LLM_TEXT = """# Some Intro
Source: https://docs.agno.com/introduction

Welcome to Agno.
---
# Shell Tool
Source: https://docs.agno.com/tools/shell

Use the shell tool to run commands.
---
# Agent Basics
Source: https://docs.agno.com/agents/overview

Build agents with Agno.
---
# Evals
Source: https://docs.agno.com/evals/getting-started

Run evals on your agents.
---
# Memory
Source: https://docs.agno.com/memory/overview

Memory lets agents remember.
---
# Deployment
Source: https://docs.agno.com/deployment/aws

Deploy to AWS."""


def test_parse_and_filter_sections_keeps_matching():
    prefixes = ["/tools/", "/agents/", "/memory/"]
    result = parse_and_filter_sections(SAMPLE_LLM_TEXT, prefixes)

    urls = [url for url, _body in result]
    assert "https://docs.agno.com/tools/shell" in urls
    assert "https://docs.agno.com/agents/overview" in urls
    assert "https://docs.agno.com/memory/overview" in urls
    assert len(result) == 3


def test_parse_and_filter_sections_drops_non_matching():
    prefixes = ["/tools/", "/agents/", "/memory/"]
    result = parse_and_filter_sections(SAMPLE_LLM_TEXT, prefixes)

    urls = [url for url, _body in result]
    assert "https://docs.agno.com/introduction" not in urls
    assert "https://docs.agno.com/evals/getting-started" not in urls
    assert "https://docs.agno.com/deployment/aws" not in urls


def test_parse_and_filter_sections_preserves_content():
    prefixes = ["/tools/"]
    result = parse_and_filter_sections(SAMPLE_LLM_TEXT, prefixes)

    assert len(result) == 1
    _url, body = result[0]
    assert "Use the shell tool" in body


def test_parse_and_filter_sections_no_matches_warns(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="vandelay.knowledge.corpus"):
        result = parse_and_filter_sections(SAMPLE_LLM_TEXT, ["/nonexistent/"])

    assert result == []
    assert "matched 0" in caplog.text


def test_parse_and_filter_sections_empty_input():
    result = parse_and_filter_sections("", ["/tools/"])
    assert result == []


def test_parse_and_filter_sections_no_source_url():
    text = "# Just a title\n\nSome content without a Source line."
    result = parse_and_filter_sections(text, ["/tools/"])
    assert result == []


# ---------------------------------------------------------------------------
# index_corpus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_corpus_calls_ainsert(tmp_path):
    """Remote source is downloaded, filtered, and inserted as Documents."""
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()

    fake_text = (
        "# Tools Overview\n"
        "Source: https://docs.agno.com/tools/overview\n\n"
        "Tool docs here.\n"
        "---\n"
        "# Evals\n"
        "Source: https://docs.agno.com/evals/intro\n\n"
        "Eval docs here."
    )

    mock_response = MagicMock()
    mock_response.text = fake_text
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    local_text = "# Local Doc\nSome content."
    mock_file = MagicMock()
    mock_file.read_text.return_value = local_text

    mock_pkg = MagicMock()
    mock_pkg.__truediv__ = MagicMock(return_value=mock_file)

    with (
        patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch(
            "importlib.resources.files",
            return_value=mock_pkg,
        ),
    ):
        count = await index_corpus(knowledge, force=True)

    # 1 filtered section from remote + 2 local sources = 3
    assert count == 3
    assert knowledge.ainsert.call_count == 3


@pytest.mark.asyncio
async def test_index_corpus_skips_when_current(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()

    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        _save_versions(_get_current_versions())
        count = await index_corpus(knowledge, force=False)

    assert count == 0
    knowledge.ainsert.assert_not_called()


@pytest.mark.asyncio
async def test_index_corpus_force_overrides(tmp_path):
    """Force flag re-indexes even when versions match."""
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()

    fake_text = (
        "# Tools Overview\n"
        "Source: https://docs.agno.com/tools/overview\n\n"
        "Tool docs."
    )

    mock_response = MagicMock()
    mock_response.text = fake_text
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    local_text = "# Doc\nContent."
    mock_file = MagicMock()
    mock_file.read_text.return_value = local_text
    mock_pkg = MagicMock()
    mock_pkg.__truediv__ = MagicMock(return_value=mock_file)

    with (
        patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("importlib.resources.files", return_value=mock_pkg),
    ):
        _save_versions(_get_current_versions())
        count = await index_corpus(knowledge, force=True)

    assert count > 0
    assert knowledge.ainsert.call_count > 0


@pytest.mark.asyncio
async def test_index_corpus_partial_failure(tmp_path):
    """If one source fails, others still get indexed."""
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()

    # Remote download fails
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("network error")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # Local sources succeed
    local_text = "# Doc\nContent."
    mock_file = MagicMock()
    mock_file.read_text.return_value = local_text
    mock_pkg = MagicMock()
    mock_pkg.__truediv__ = MagicMock(return_value=mock_file)

    with (
        patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("importlib.resources.files", return_value=mock_pkg),
    ):
        count = await index_corpus(knowledge, force=True)

    # Only the 2 local sources succeed
    assert count == 2
    assert versions_file.exists()


@pytest.mark.asyncio
async def test_index_local_source(tmp_path):
    """Local source reads from vandelay.docs package and inserts Document."""
    from vandelay.knowledge.corpus import _index_local

    knowledge = AsyncMock()
    source = LocalCorpusSource("Test Doc", "TEST.md")

    mock_file = MagicMock()
    mock_file.read_text.return_value = "# Test\nContent here."
    mock_pkg = MagicMock()
    mock_pkg.__truediv__ = MagicMock(return_value=mock_file)

    with patch("importlib.resources.files", return_value=mock_pkg) as mock_files:
        result = await _index_local(knowledge, source)

    assert result == 1
    mock_files.assert_called_once_with("vandelay.docs")
    knowledge.ainsert.assert_called_once()
    call_kwargs = knowledge.ainsert.call_args[1]
    assert len(call_kwargs["documents"]) == 1
    assert call_kwargs["documents"][0].name == "Test Doc"


# ---------------------------------------------------------------------------
# CORPUS_SOURCES / CORPUS_URLS validation
# ---------------------------------------------------------------------------


def test_corpus_sources_valid():
    """All sources have names; remote sources have HTTPS URLs."""
    seen_names = set()
    for source in CORPUS_SOURCES:
        assert source.name, "Source must have a name"
        assert source.name not in seen_names, f"Duplicate name: {source.name}"
        seen_names.add(source.name)

        if isinstance(source, RemoteCorpusSource):
            assert source.url.startswith("https://"), f"{source.name}: URL must be HTTPS"
        elif isinstance(source, LocalCorpusSource):
            assert source.filename.endswith(".md"), f"{source.name}: expected .md file"


def test_corpus_urls_valid():
    """Backward-compat CORPUS_URLS list is consistent with CORPUS_SOURCES."""
    seen = set()
    for name, url in CORPUS_URLS:
        assert url.startswith("https://"), f"{name}: URL must be HTTPS"
        assert url not in seen, f"Duplicate URL: {url}"
        seen.add(url)

    # Should match remote sources
    remote_sources = [s for s in CORPUS_SOURCES if isinstance(s, RemoteCorpusSource)]
    assert len(CORPUS_URLS) == len(remote_sources)


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def test_refresh_cli_up_to_date():
    from typer.testing import CliRunner

    from vandelay.cli.knowledge_commands import app

    runner = CliRunner()

    with (
        patch("vandelay.cli.knowledge_commands._ensure_knowledge") as mock_ek,
        patch(
            "vandelay.knowledge.corpus.corpus_needs_refresh", return_value=False
        ),
    ):
        mock_ek.return_value = (AsyncMock(), AsyncMock())
        result = runner.invoke(app, ["refresh"])

    assert "up to date" in result.output


def test_refresh_cli_force():
    from typer.testing import CliRunner

    from vandelay.cli.knowledge_commands import app

    runner = CliRunner()

    with (
        patch("vandelay.cli.knowledge_commands._ensure_knowledge") as mock_ek,
        patch(
            "vandelay.knowledge.corpus.index_corpus", return_value=3
        ) as mock_idx,
    ):
        mock_ek.return_value = (AsyncMock(), AsyncMock())
        result = runner.invoke(app, ["refresh", "--force"])

    mock_idx.assert_called_once()
    assert "Indexed 3 source(s)" in result.output
