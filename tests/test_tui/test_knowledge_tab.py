"""Tests for KnowledgeTab."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestKnowledgeTabCompose:
    def test_imports_cleanly(self):
        from vandelay.tui.tabs.knowledge import KnowledgeTab
        assert KnowledgeTab is not None

    def test_key_widget_ids_defined(self):
        """Verify expected widget IDs exist in the compose output."""
        import inspect
        from vandelay.tui.tabs.knowledge import KnowledgeTab
        src = inspect.getsource(KnowledgeTab.compose)
        for wid in ["kb-enabled", "kb-stat-embedder", "kb-stat-path", "kb-stat-count",
                    "kb-path-input", "btn-kb-add", "btn-kb-refresh-status",
                    "btn-kb-refresh-corpus", "btn-kb-clear", "kb-result"]:
            assert wid in src, f"Missing widget id: {wid}"


class TestKnowledgeSaveEnabled:
    def _make_tab(self):
        from vandelay.tui.tabs.knowledge import KnowledgeTab
        tab = KnowledgeTab.__new__(KnowledgeTab)
        return tab

    def test_save_enabled_writes_to_settings(self):
        from vandelay.tui.tabs.knowledge import KnowledgeTab
        tab = self._make_tab()
        mock_switch = MagicMock()
        mock_switch.value = True
        tab.query_one = lambda sel, cls=None: mock_switch
        mock_settings = MagicMock()
        mock_app = MagicMock()

        with patch.object(KnowledgeTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            with patch("vandelay.config.settings.get_settings") as mock_gs:
                mock_gs.return_value = mock_settings
                tab._save_enabled()

        assert mock_settings.knowledge.enabled is True
        mock_settings.save.assert_called_once()

    def test_save_enabled_notifies_on_error(self):
        from vandelay.tui.tabs.knowledge import KnowledgeTab
        tab = self._make_tab()
        tab.query_one = MagicMock(side_effect=RuntimeError("boom"))
        mock_app = MagicMock()

        with patch.object(KnowledgeTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            tab._save_enabled()

        mock_app.notify.assert_called_once()
        assert mock_app.notify.call_args[1].get("severity") == "error"


class TestKnowledgeMainScreenRegistration:
    def test_knowledge_tab_in_main_screen(self):
        import inspect
        from vandelay.tui.screens.main import MainScreen
        src = inspect.getsource(MainScreen.compose)
        assert "KnowledgeTab" in src
        assert "tab-knowledge" in src
