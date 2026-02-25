"""Tests for MemoryTab."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestMemoryTabCompose:
    def test_imports_cleanly(self):
        from vandelay.tui.tabs.memory import MemoryTab
        assert MemoryTab is not None

    def test_key_widget_ids_defined(self):
        import inspect
        from vandelay.tui.tabs.memory import MemoryTab
        src = inspect.getsource(MemoryTab.compose)
        for wid in ["mem-toolbar", "mem-table", "mem-status",
                    "btn-mem-refresh", "btn-mem-delete", "btn-mem-clear"]:
            assert wid in src, f"Missing widget id: {wid}"


class TestMemoryLoadMemories:
    def _make_tab(self):
        from vandelay.tui.tabs.memory import MemoryTab
        tab = MemoryTab.__new__(MemoryTab)
        tab._memories = []
        return tab

    def test_load_populates_table(self):
        from datetime import datetime, timezone
        from vandelay.tui.tabs.memory import MemoryTab

        tab = self._make_tab()

        mock_mem = MagicMock()
        mock_mem.memory_id = "abc123def456"
        mock_mem.memory = "User prefers concise answers"
        mock_mem.topics = ["preferences"]
        mock_mem.created_at = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())

        mock_table = MagicMock()
        mock_status = MagicMock()

        def mock_query_one(sel, cls=None):
            if "mem-table" in sel:
                return mock_table
            if "mem-status" in sel:
                return mock_status
            raise ValueError(sel)

        tab.query_one = mock_query_one

        mock_db = MagicMock()
        mock_db.get_user_memories.return_value = [mock_mem]
        mock_settings = MagicMock()
        mock_settings.user_id = "test-user"

        with patch("vandelay.config.settings.get_settings", return_value=mock_settings):
            with patch("vandelay.memory.setup.create_db", return_value=mock_db):
                tab._load_memories()

        mock_table.clear.assert_called_once_with(columns=False)
        mock_table.add_row.assert_called_once()
        row_args = mock_table.add_row.call_args[0]
        assert row_args[0] == "abc123de"   # first 8 chars of memory_id
        assert "preferences" in row_args[1]
        assert "User prefers" in row_args[2]

    def test_load_handles_empty(self):
        from vandelay.tui.tabs.memory import MemoryTab
        tab = self._make_tab()
        mock_table = MagicMock()
        mock_status = MagicMock()

        def mock_query_one(sel, cls=None):
            if "mem-table" in sel:
                return mock_table
            if "mem-status" in sel:
                return mock_status
            raise ValueError(sel)

        tab.query_one = mock_query_one
        mock_db = MagicMock()
        mock_db.get_user_memories.return_value = []
        mock_settings = MagicMock()
        mock_settings.user_id = ""

        with patch("vandelay.config.settings.get_settings", return_value=mock_settings):
            with patch("vandelay.memory.setup.create_db", return_value=mock_db):
                tab._load_memories()

        assert tab._memories == []
        mock_status.update.assert_called_once_with("0 memories")

    def test_load_handles_exception(self):
        from vandelay.tui.tabs.memory import MemoryTab
        tab = self._make_tab()
        mock_status = MagicMock()
        tab.query_one = lambda sel, cls=None: mock_status

        with patch("vandelay.config.settings.get_settings", side_effect=RuntimeError("no config")):
            tab._load_memories()

        assert tab._memories == []
        mock_status.update.assert_called_once()
        assert "Load failed" in mock_status.update.call_args[0][0]


class TestMemoryDeleteSelected:
    def _make_tab(self):
        from vandelay.tui.tabs.memory import MemoryTab
        tab = MemoryTab.__new__(MemoryTab)
        tab._memories = []
        return tab

    def test_delete_calls_db(self):
        from vandelay.tui.tabs.memory import MemoryTab
        tab = self._make_tab()

        mock_row_key = MagicMock()
        mock_row_key.value = "mem-id-123"
        mock_table = MagicMock()
        mock_table.cursor_row_key = mock_row_key

        # patch _load_memories to avoid DB call on reload
        tab._load_memories = MagicMock()
        mock_app = MagicMock()

        def mock_query_one(sel, cls=None):
            if "mem-table" in sel:
                return mock_table
            raise ValueError(sel)

        tab.query_one = mock_query_one

        mock_db = MagicMock()
        mock_settings = MagicMock()
        mock_settings.user_id = "user1"

        with patch.object(MemoryTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            with patch("vandelay.config.settings.get_settings", return_value=mock_settings):
                with patch("vandelay.memory.setup.create_db", return_value=mock_db):
                    tab._delete_selected()

        mock_db.delete_user_memory.assert_called_once_with(
            memory_id="mem-id-123", user_id="user1"
        )

    def test_delete_warns_when_no_selection(self):
        from vandelay.tui.tabs.memory import MemoryTab
        tab = self._make_tab()

        mock_table = MagicMock()
        mock_table.cursor_row_key = None
        tab.query_one = lambda sel, cls=None: mock_table
        mock_app = MagicMock()

        with patch.object(MemoryTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            tab._delete_selected()

        mock_app.notify.assert_called_once()
        assert mock_app.notify.call_args[1].get("severity") == "warning"


class TestMemoryMainScreenRegistration:
    def test_memory_tab_in_main_screen(self):
        import inspect
        from vandelay.tui.screens.main import MainScreen
        src = inspect.getsource(MainScreen.compose)
        assert "MemoryTab" in src
        assert "tab-memory" in src
