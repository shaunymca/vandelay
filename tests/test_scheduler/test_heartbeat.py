"""Tests for heartbeat job synchronization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vandelay.config.models import HeartbeatConfig
from vandelay.core.chat_service import ChatResponse
from vandelay.scheduler.engine import HEARTBEAT_COMMAND, HEARTBEAT_JOB_ID, SchedulerEngine
from vandelay.scheduler.models import JobType
from vandelay.scheduler.store import CronJobStore


@pytest.fixture
def mock_chat_service():
    svc = AsyncMock()
    svc.run = AsyncMock(return_value=ChatResponse(content="HEARTBEAT_OK"))
    return svc


@pytest.fixture
def store(tmp_path: Path) -> CronJobStore:
    return CronJobStore(path=tmp_path / "cron_jobs.json")


def _make_settings(enabled=True, interval=30, start=8, end=22, tz="UTC"):
    settings = MagicMock()
    settings.heartbeat = HeartbeatConfig(
        enabled=enabled,
        interval_minutes=interval,
        active_hours_start=start,
        active_hours_end=end,
        timezone=tz,
    )
    settings.timezone = "UTC"
    return settings


def test_heartbeat_creates_job_when_enabled(mock_chat_service, store):
    """When heartbeat is enabled, _sync_heartbeat_job should create a job."""
    settings = _make_settings(enabled=True, interval=30, start=8, end=22)
    engine = SchedulerEngine(settings, mock_chat_service, store)
    engine._sync_heartbeat_job()

    job = store.get(HEARTBEAT_JOB_ID)
    assert job is not None
    assert job.job_type == JobType.HEARTBEAT
    assert job.cron_expression == "*/30 8-22 * * *"
    assert job.command == HEARTBEAT_COMMAND


def test_heartbeat_not_created_when_disabled(mock_chat_service, store):
    """When heartbeat is disabled, no heartbeat job should be created."""
    settings = _make_settings(enabled=False)
    engine = SchedulerEngine(settings, mock_chat_service, store)
    engine._sync_heartbeat_job()

    assert store.get(HEARTBEAT_JOB_ID) is None


def test_heartbeat_removed_when_disabled(mock_chat_service, store):
    """If heartbeat is disabled but a heartbeat job exists, it should be removed."""
    # First create with enabled
    settings_on = _make_settings(enabled=True)
    engine_on = SchedulerEngine(settings_on, mock_chat_service, store)
    engine_on._sync_heartbeat_job()
    assert store.get(HEARTBEAT_JOB_ID) is not None

    # Then disable
    settings_off = _make_settings(enabled=False)
    engine_off = SchedulerEngine(settings_off, mock_chat_service, store)
    engine_off._sync_heartbeat_job()
    assert store.get(HEARTBEAT_JOB_ID) is None


def test_heartbeat_updates_when_config_changes(mock_chat_service, store):
    """If heartbeat config changes, the existing job should be updated."""
    settings1 = _make_settings(enabled=True, interval=30, start=8, end=22)
    engine1 = SchedulerEngine(settings1, mock_chat_service, store)
    engine1._sync_heartbeat_job()

    job1 = store.get(HEARTBEAT_JOB_ID)
    assert job1.cron_expression == "*/30 8-22 * * *"

    # Change interval and hours
    settings2 = _make_settings(enabled=True, interval=15, start=6, end=20)
    engine2 = SchedulerEngine(settings2, mock_chat_service, store)
    engine2._sync_heartbeat_job()

    job2 = store.get(HEARTBEAT_JOB_ID)
    assert job2.cron_expression == "*/15 6-20 * * *"


def test_heartbeat_uses_config_timezone(mock_chat_service, store):
    """Heartbeat should use the timezone from HeartbeatConfig."""
    settings = _make_settings(enabled=True, tz="US/Eastern")
    engine = SchedulerEngine(settings, mock_chat_service, store)
    engine._sync_heartbeat_job()

    job = store.get(HEARTBEAT_JOB_ID)
    assert job.timezone == "US/Eastern"


@pytest.mark.asyncio
async def test_heartbeat_execution_ok(mock_chat_service, store):
    """Heartbeat execution with HEARTBEAT_OK should log debug (no error)."""
    settings = _make_settings(enabled=True)
    engine = SchedulerEngine(settings, mock_chat_service, store)
    engine._sync_heartbeat_job()

    await engine._execute_job(HEARTBEAT_JOB_ID)

    job = store.get(HEARTBEAT_JOB_ID)
    assert job.run_count == 1
    assert "HEARTBEAT_OK" in job.last_result


@pytest.mark.asyncio
async def test_heartbeat_execution_alert(mock_chat_service, store):
    """Heartbeat with non-OK response should still update the job."""
    mock_chat_service.run = AsyncMock(
        return_value=ChatResponse(content="Alert: disk space critical")
    )
    settings = _make_settings(enabled=True)
    engine = SchedulerEngine(settings, mock_chat_service, store)
    engine._sync_heartbeat_job()

    await engine._execute_job(HEARTBEAT_JOB_ID)

    job = store.get(HEARTBEAT_JOB_ID)
    assert job.run_count == 1
    assert "disk space" in job.last_result


@pytest.mark.asyncio
async def test_heartbeat_synced_on_start(mock_chat_service, store):
    """start() should sync the heartbeat job from config."""
    settings = _make_settings(enabled=True, interval=10, start=9, end=21)
    engine = SchedulerEngine(settings, mock_chat_service, store)

    await engine.start()

    job = store.get(HEARTBEAT_JOB_ID)
    assert job is not None
    assert job.cron_expression == "*/10 9-21 * * *"

    await engine.stop()
