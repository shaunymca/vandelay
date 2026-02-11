"""Tests for the SchedulerEngine."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vandelay.config.models import HeartbeatConfig
from vandelay.core.chat_service import ChatResponse
from vandelay.scheduler.engine import SchedulerEngine
from vandelay.scheduler.models import CronJob, JobType
from vandelay.scheduler.store import CronJobStore


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.heartbeat = HeartbeatConfig(enabled=False)
    settings.timezone = "UTC"
    return settings


@pytest.fixture
def mock_chat_service():
    svc = AsyncMock()
    svc.run = AsyncMock(return_value=ChatResponse(content="Done"))
    return svc


@pytest.fixture
def store(tmp_path: Path) -> CronJobStore:
    return CronJobStore(path=tmp_path / "cron_jobs.json")


@pytest.fixture
def engine(mock_settings, mock_chat_service, store) -> SchedulerEngine:
    return SchedulerEngine(mock_settings, mock_chat_service, store)


def test_add_job(engine: SchedulerEngine):
    """add_job should store a job and compute next_run."""
    job = CronJob(name="Test", cron_expression="*/5 * * * *", command="hello")
    result = engine.add_job(job)
    assert result.next_run is not None
    assert engine.get_job(result.id) is not None


def test_add_job_invalid_cron(engine: SchedulerEngine):
    """add_job should reject invalid cron expressions."""
    job = CronJob(name="Bad", cron_expression="not a cron", command="nope")
    with pytest.raises(ValueError, match="Invalid cron expression"):
        engine.add_job(job)


def test_remove_job(engine: SchedulerEngine):
    """remove_job should delete the job."""
    job = CronJob(name="Delete Me", cron_expression="0 * * * *", command="bye")
    engine.add_job(job)
    assert engine.remove_job(job.id) is True
    assert engine.get_job(job.id) is None


def test_remove_nonexistent(engine: SchedulerEngine):
    """remove_job for a missing ID should return False."""
    assert engine.remove_job("nope") is False


def test_pause_job(engine: SchedulerEngine):
    """pause_job should set enabled=False."""
    job = CronJob(name="Pause Me", cron_expression="0 * * * *", command="wait")
    engine.add_job(job)
    paused = engine.pause_job(job.id)
    assert paused is not None
    assert paused.enabled is False


def test_pause_nonexistent(engine: SchedulerEngine):
    """pause_job for a missing ID should return None."""
    assert engine.pause_job("nope") is None


def test_resume_job(engine: SchedulerEngine):
    """resume_job should re-enable a paused job."""
    job = CronJob(name="Resume Me", cron_expression="0 * * * *", command="go")
    engine.add_job(job)
    engine.pause_job(job.id)
    resumed = engine.resume_job(job.id)
    assert resumed is not None
    assert resumed.enabled is True
    assert resumed.next_run is not None


def test_resume_nonexistent(engine: SchedulerEngine):
    """resume_job for a missing ID should return None."""
    assert engine.resume_job("nope") is None


def test_list_jobs(engine: SchedulerEngine):
    """list_jobs should return all stored jobs."""
    engine.add_job(CronJob(name="A", cron_expression="0 * * * *", command="a"))
    engine.add_job(CronJob(name="B", cron_expression="0 * * * *", command="b"))
    assert len(engine.list_jobs()) == 2


def test_get_job(engine: SchedulerEngine):
    """get_job should return a specific job."""
    job = CronJob(name="Get Me", cron_expression="0 * * * *", command="found")
    engine.add_job(job)
    fetched = engine.get_job(job.id)
    assert fetched is not None
    assert fetched.name == "Get Me"


@pytest.mark.asyncio
async def test_execute_job(engine: SchedulerEngine, mock_chat_service):
    """_execute_job should call ChatService.run and update job metadata."""
    job = CronJob(name="Exec", cron_expression="* * * * *", command="run this")
    engine.add_job(job)

    await engine._execute_job(job.id)

    # ChatService was called
    mock_chat_service.run.assert_called_once()
    call_msg = mock_chat_service.run.call_args[0][0]
    assert call_msg.text == "run this"
    assert call_msg.channel == "scheduler"

    # Job metadata updated
    updated = engine.get_job(job.id)
    assert updated.run_count == 1
    assert updated.last_run is not None
    assert updated.last_result == "Done"


@pytest.mark.asyncio
async def test_execute_job_missing(engine: SchedulerEngine, mock_chat_service):
    """_execute_job should handle a missing job gracefully."""
    await engine._execute_job("doesnotexist")
    mock_chat_service.run.assert_not_called()


@pytest.mark.asyncio
async def test_start_stop(engine: SchedulerEngine):
    """Engine start/stop should not raise."""
    await engine.start()
    assert engine._scheduler.running
    await engine.stop()


@pytest.mark.asyncio
async def test_start_loads_enabled_jobs(engine: SchedulerEngine):
    """start() should register all enabled jobs."""
    engine.add_job(CronJob(name="A", cron_expression="0 * * * *", command="a"))
    engine.add_job(CronJob(name="B", cron_expression="0 * * * *", command="b", enabled=False))

    # Stop if already started by add_job
    if engine._scheduler.running:
        await engine.stop()

    with patch.object(engine, "_register_job") as mock_reg:
        await engine.start()
        # Only the enabled job should be registered (disabled one skipped)
        registered_ids = [call.args[0].id for call in mock_reg.call_args_list]
        enabled_ids = [j.id for j in engine.list_jobs() if j.enabled]
        for eid in enabled_ids:
            assert eid in registered_ids

    await engine.stop()
