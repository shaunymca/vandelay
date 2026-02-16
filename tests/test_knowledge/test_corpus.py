"""Tests for the built-in documentation corpus."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from vandelay.knowledge.corpus import (
    CORPUS_URLS,
    _get_current_versions,
    _get_stored_versions,
    _save_versions,
    corpus_needs_refresh,
    index_corpus,
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
# index_corpus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_corpus_calls_ainsert(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()

    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        count = await index_corpus(knowledge, force=True)

    assert count == len(CORPUS_URLS)
    assert knowledge.ainsert.call_count == len(CORPUS_URLS)
    for (name, url), call in zip(CORPUS_URLS, knowledge.ainsert.call_args_list):
        assert call == ((), {"url": url, "name": name})


@pytest.mark.asyncio
async def test_index_corpus_partial_failure(tmp_path):
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()
    # First call raises, rest succeed
    knowledge.ainsert.side_effect = [Exception("boom")] + [None] * (len(CORPUS_URLS) - 1)

    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        count = await index_corpus(knowledge, force=True)

    # Only successes counted, but versions still saved
    assert count == len(CORPUS_URLS) - 1
    assert versions_file.exists()


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
    versions_file = tmp_path / "data" / "corpus_versions.json"
    knowledge = AsyncMock()

    with patch("vandelay.knowledge.corpus.CORPUS_VERSIONS_FILE", versions_file):
        _save_versions(_get_current_versions())
        count = await index_corpus(knowledge, force=True)

    assert count == len(CORPUS_URLS)
    assert knowledge.ainsert.call_count == len(CORPUS_URLS)


# ---------------------------------------------------------------------------
# CORPUS_URLS validation
# ---------------------------------------------------------------------------


def test_corpus_urls_valid():
    seen = set()
    for name, url in CORPUS_URLS:
        assert url.startswith("https://"), f"{name}: URL must be HTTPS"
        assert url not in seen, f"Duplicate URL: {url}"
        seen.add(url)


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
            "vandelay.knowledge.corpus.index_corpus", return_value=1
        ) as mock_idx,
    ):
        mock_ek.return_value = (AsyncMock(), AsyncMock())
        result = runner.invoke(app, ["refresh", "--force"])

    mock_idx.assert_called_once()
    assert "Indexed 1 URL(s)" in result.output
