"""Tests for the DeepWorkTools agent toolkit."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vandelay.core.deep_work import DeepWorkSession, SessionStatus
from vandelay.tools.deep_work import DeepWorkTools


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    return manager


@pytest.fixture
def toolkit(mock_manager) -> DeepWorkTools:
    return DeepWorkTools(manager=mock_manager)


class TestDeepWorkToolsRegistration:
    """Verify all tools are registered."""

    def test_toolkit_name(self, toolkit):
        assert toolkit.name == "deep_work"

    def test_has_start_tool(self, toolkit):
        names = list(toolkit.functions.keys())
        assert "start_deep_work" in names

    def test_has_status_tool(self, toolkit):
        names = list(toolkit.functions.keys())
        assert "check_deep_work_status" in names

    def test_has_cancel_tool(self, toolkit):
        names = list(toolkit.functions.keys())
        assert "cancel_deep_work" in names


class TestCheckStatus:
    def test_check_status_delegates(self, toolkit, mock_manager):
        mock_manager.get_status.return_value = "Session running"
        result = toolkit.check_deep_work_status()
        assert result == "Session running"
        mock_manager.get_status.assert_called_once()


class TestCancelDeepWork:
    def test_cancel_delegates(self, toolkit, mock_manager):
        mock_manager.cancel_session.return_value = "Session cancelled"
        result = toolkit.cancel_deep_work()
        assert result == "Session cancelled"
        mock_manager.cancel_session.assert_called_once()

    def test_cancel_no_session(self, toolkit, mock_manager):
        mock_manager.cancel_session.return_value = "No active deep work session to cancel."
        result = toolkit.cancel_deep_work()
        assert "No active" in result
