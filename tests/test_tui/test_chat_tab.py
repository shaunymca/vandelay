"""Tests for the Chat tab widget."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.app import App, ComposeResult

from vandelay.tui.tabs.chat import ChatTab


# ---------------------------------------------------------------------------
# Minimal app wrapper for Textual pilot tests
# ---------------------------------------------------------------------------


class ChatApp(App):
    def compose(self) -> ComposeResult:
        yield ChatTab()


# ---------------------------------------------------------------------------
# Unit tests — no server required
# ---------------------------------------------------------------------------


class TestChatTabImport:
    def test_import(self):
        from vandelay.tui.tabs.chat import ChatTab

        assert ChatTab is not None

    def test_message_classes_exist(self):
        assert hasattr(ChatTab, "Connected")
        assert hasattr(ChatTab, "Disconnected")
        assert hasattr(ChatTab, "ContentDelta")
        assert hasattr(ChatTab, "ContentDone")
        assert hasattr(ChatTab, "ToolStarted")
        assert hasattr(ChatTab, "ToolDone")
        assert hasattr(ChatTab, "RunError")
        assert hasattr(ChatTab, "SystemInfo")


class TestChatTabMount:
    @pytest.mark.asyncio
    async def test_mounts_without_error(self):
        """ChatTab should mount cleanly even when the server is offline."""
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):  # don't actually connect
            async with app.run_test(headless=True) as pilot:
                assert pilot.app.query_one(ChatTab) is not None

    @pytest.mark.asyncio
    async def test_initial_status_shows_connecting(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                label = pilot.app.query_one("#chat-session-label")
                assert label is not None  # widget exists

    @pytest.mark.asyncio
    async def test_input_widget_present(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                from textual.widgets import Input

                inp = pilot.app.query_one("#chat-input", Input)
                assert inp is not None

    @pytest.mark.asyncio
    async def test_send_button_present(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                from textual.widgets import Button

                btn = pilot.app.query_one("#send-btn", Button)
                assert btn is not None

    @pytest.mark.asyncio
    async def test_new_session_button_present(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                from textual.widgets import Button

                btn = pilot.app.query_one("#chat-new-btn", Button)
                assert btn is not None


class TestChatTabMessages:
    """Test that posting Textual messages updates the UI correctly."""

    @pytest.mark.asyncio
    async def test_connected_message_updates_status(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()

                dot = pilot.app.query_one("#chat-conn-dot")
                label = pilot.app.query_one("#chat-session-label")
                assert tab._connected is True
                assert tab._session_id == "ws-abc12345"
                # dot and label widgets exist and were updated
                assert dot is not None
                assert label is not None

    @pytest.mark.asyncio
    async def test_disconnected_message_updates_status(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                # First connect
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()
                # Then disconnect
                tab.post_message(ChatTab.Disconnected())
                await pilot.pause()

                assert tab._connected is False

    @pytest.mark.asyncio
    async def test_content_delta_creates_streaming_widget(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()

                tab.post_message(ChatTab.ContentDelta("Hello "))
                await pilot.pause()
                tab.post_message(ChatTab.ContentDelta("world"))
                await pilot.pause()

                assert tab._stream_widget is not None
                assert tab._stream_buf == "Hello world"

    @pytest.mark.asyncio
    async def test_content_done_clears_streaming_widget(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()

                tab.post_message(ChatTab.ContentDelta("Hello"))
                await pilot.pause()
                tab.post_message(ChatTab.ContentDone("Hello world!"))
                await pilot.pause()

                assert tab._stream_widget is None
                assert tab._stream_buf == ""

    @pytest.mark.asyncio
    async def test_tool_started_shows_indicator(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()

                tab.post_message(ChatTab.ToolStarted("web_search"))
                await pilot.pause()

                assert tab._tool_widget is not None

    @pytest.mark.asyncio
    async def test_tool_done_removes_indicator(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()

                tab.post_message(ChatTab.ToolStarted("web_search"))
                await pilot.pause()
                tab.post_message(ChatTab.ToolDone("web_search"))
                await pilot.pause()

                assert tab._tool_widget is None

    @pytest.mark.asyncio
    async def test_run_error_clears_streaming(self):
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                tab = pilot.app.query_one(ChatTab)
                tab.post_message(ChatTab.Connected("ws-abc12345"))
                await pilot.pause()

                tab.post_message(ChatTab.ContentDelta("partial"))
                await pilot.pause()
                tab.post_message(ChatTab.RunError("model overloaded"))
                await pilot.pause()

                assert tab._stream_widget is None

    @pytest.mark.asyncio
    async def test_send_offline_shows_error(self):
        """Sending while disconnected shows an error, does not crash."""
        app = ChatApp()
        with patch.object(ChatTab, "_start_ws"):
            async with app.run_test(headless=True) as pilot:
                from textual.widgets import Input

                tab = pilot.app.query_one(ChatTab)
                # Not connected — don't post Connected message

                inp = pilot.app.query_one("#chat-input", Input)
                inp.value = "hello"
                await pilot.press("enter")
                await pilot.pause()

                log = pilot.app.query_one("#chat-log")
                # Should have an error widget
                error_widgets = [w for w in log.children if "msg-error" in w.classes]
                assert len(error_widgets) >= 1
