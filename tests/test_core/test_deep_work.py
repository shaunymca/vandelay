"""Tests for the DeepWorkManager session lifecycle."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vandelay.core.deep_work import DeepWorkManager, DeepWorkSession, SessionStatus


@pytest.fixture
def mock_settings():
    """Create mock settings with deep work enabled."""
    settings = MagicMock()
    settings.deep_work.enabled = True
    settings.deep_work.background = True
    settings.deep_work.activation = "suggest"
    settings.deep_work.max_iterations = 10
    settings.deep_work.max_time_minutes = 30
    settings.deep_work.progress_interval_minutes = 5
    settings.deep_work.progress_channel = ""
    settings.deep_work.save_results_to_workspace = False
    settings.user_id = "test-user"
    settings.workspace_dir = "/tmp/test-workspace"
    settings.team.members = []
    settings.model.provider = "anthropic"
    settings.model.model_id = "claude-sonnet-4-5-20250929"
    settings.model.auth_method = "api_key"
    settings.enabled_tools = []
    settings.agent_name = "TestAgent"
    return settings


@pytest.fixture
def manager(mock_settings):
    return DeepWorkManager(settings=mock_settings)


# -- Session dataclass tests --------------------------------------------------


class TestDeepWorkSession:
    def test_default_values(self):
        session = DeepWorkSession()
        assert session.status == SessionStatus.pending
        assert session.objective == ""
        assert len(session.id) == 12

    def test_elapsed_minutes_not_started(self):
        session = DeepWorkSession()
        assert session.elapsed_minutes == 0.0

    def test_elapsed_minutes_running(self):
        session = DeepWorkSession(started_at=datetime.now(UTC))
        assert session.elapsed_minutes >= 0.0

    def test_is_active_pending(self):
        session = DeepWorkSession(status=SessionStatus.pending)
        assert session.is_active is True

    def test_is_active_running(self):
        session = DeepWorkSession(status=SessionStatus.running)
        assert session.is_active is True

    def test_is_active_completed(self):
        session = DeepWorkSession(status=SessionStatus.completed)
        assert session.is_active is False

    def test_is_active_cancelled(self):
        session = DeepWorkSession(status=SessionStatus.cancelled)
        assert session.is_active is False

    def test_is_active_failed(self):
        session = DeepWorkSession(status=SessionStatus.failed)
        assert session.is_active is False

    def test_is_active_timed_out(self):
        session = DeepWorkSession(status=SessionStatus.timed_out)
        assert session.is_active is False


# -- Manager tests -------------------------------------------------------------


class TestDeepWorkManager:
    def test_initial_state(self, manager):
        assert manager.current_session is None

    def test_get_status_no_session(self, manager):
        status = manager.get_status()
        assert "No deep work sessions" in status

    def test_cancel_no_session(self, manager):
        result = manager.cancel_session()
        assert "No active" in result

    @pytest.mark.asyncio
    async def test_start_session_rejects_duplicate(self, manager):
        """Cannot start a new session while one is active."""
        manager._session = DeepWorkSession(
            objective="existing", status=SessionStatus.running
        )
        result = await manager.start_session("new task")
        assert "already active" in result

    @pytest.mark.asyncio
    async def test_start_session_blocking_mode(self, mock_settings):
        """Blocking mode awaits session completion directly."""
        mock_settings.deep_work.background = False
        mgr = DeepWorkManager(settings=mock_settings)

        # Mock the actual run to avoid building a real team
        async def fake_run(session):
            session.status = SessionStatus.completed
            session.result = "Done"
            session.finished_at = datetime.now(UTC)

        with patch.object(mgr, "_run_session", side_effect=fake_run):
            result = await mgr.start_session("test objective")

        assert "completed" in result

    def test_cancel_active_session(self, manager):
        """Cancelling an active session sets status and timestamp."""
        session = DeepWorkSession(
            objective="test",
            status=SessionStatus.running,
            started_at=datetime.now(UTC),
        )
        manager._session = session
        manager._task = MagicMock()
        manager._task.done.return_value = False

        result = manager.cancel_session()
        assert "cancelled" in result
        assert session.status == SessionStatus.cancelled
        assert session.finished_at is not None

    def test_get_status_with_session(self, manager):
        """Status includes session details."""
        session = DeepWorkSession(
            objective="Research AI trends",
            status=SessionStatus.running,
            started_at=datetime.now(UTC),
            max_iterations=50,
        )
        manager._session = session

        status = manager.get_status()
        assert "Research AI trends" in status
        assert "running" in status
        assert "50" in status

    def test_get_status_with_result(self, manager):
        """Completed session status includes result preview."""
        session = DeepWorkSession(
            objective="Test",
            status=SessionStatus.completed,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            result="This is the full result of the deep work session.",
        )
        manager._session = session

        status = manager.get_status()
        assert "This is the full result" in status

    def test_get_status_truncates_long_result(self, manager):
        """Long results are truncated in status display."""
        session = DeepWorkSession(
            objective="Test",
            status=SessionStatus.completed,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            result="x" * 1000,
        )
        manager._session = session

        status = manager.get_status()
        assert "truncated" in status


class TestDeepWorkSessionStatus:
    """Test the SessionStatus enum values."""

    def test_all_statuses(self):
        assert SessionStatus.pending.value == "pending"
        assert SessionStatus.running.value == "running"
        assert SessionStatus.completed.value == "completed"
        assert SessionStatus.cancelled.value == "cancelled"
        assert SessionStatus.timed_out.value == "timed_out"
        assert SessionStatus.failed.value == "failed"
