"""Tests for vector DB factory (ChromaDB/LanceDB fallback)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.knowledge.vectordb import create_vector_db, get_vector_count


class TestCreateVectorDb:
    def test_prefers_chromadb_when_available(self):
        """ChromaDB is tried first when importable."""
        mock_embedder = MagicMock()
        mock_chroma = MagicMock()

        with patch(
            "vandelay.knowledge.vectordb._try_chromadb", return_value=mock_chroma
        ) as try_chroma:
            result = create_vector_db(mock_embedder)
            assert result is mock_chroma
            try_chroma.assert_called_once_with(mock_embedder, "vandelay_knowledge")

    def test_falls_back_to_lancedb(self):
        """LanceDB is used when ChromaDB is unavailable."""
        mock_embedder = MagicMock()
        mock_lance = MagicMock()

        with (
            patch("vandelay.knowledge.vectordb._try_chromadb", return_value=None),
            patch(
                "vandelay.knowledge.vectordb._try_lancedb", return_value=mock_lance
            ) as try_lance,
        ):
            result = create_vector_db(mock_embedder)
            assert result is mock_lance
            try_lance.assert_called_once_with(mock_embedder, "vandelay_knowledge")

    def test_returns_none_when_neither_available(self):
        """Returns None when both ChromaDB and LanceDB are unavailable."""
        mock_embedder = MagicMock()

        with (
            patch("vandelay.knowledge.vectordb._try_chromadb", return_value=None),
            patch("vandelay.knowledge.vectordb._try_lancedb", return_value=None),
        ):
            result = create_vector_db(mock_embedder)
            assert result is None


class TestGetVectorCount:
    def test_lancedb_table_attr(self):
        """Reads count from LanceDB's .table.count_rows()."""
        vdb = MagicMock()
        vdb.table.count_rows.return_value = 42
        assert get_vector_count(vdb) == 42

    def test_chromadb_collection_attr(self):
        """Reads count from ChromaDB's ._collection.count()."""
        vdb = MagicMock(spec=[])
        vdb._collection = MagicMock()
        vdb._collection.count.return_value = 7
        assert get_vector_count(vdb) == 7

    def test_returns_zero_on_error(self):
        """Returns 0 when count can't be determined."""
        vdb = MagicMock(spec=[])
        assert get_vector_count(vdb) == 0

    def test_returns_zero_for_none_table(self):
        """Returns 0 when table is None."""
        vdb = MagicMock()
        vdb.table = None
        vdb._table = None
        # Remove chromadb attrs
        del vdb._collection
        del vdb.collection
        assert get_vector_count(vdb) == 0
