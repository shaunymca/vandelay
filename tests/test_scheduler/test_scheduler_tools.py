"""Tests for the SchedulerTools agent toolkit."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from vandelay.scheduler.models import CronJob, JobType
from vandelay.tools.scheduler import SchedulerTools


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    return engine


@pytest.fixture
def toolkit(mock_engine) -> SchedulerTools:
    return SchedulerTools(engine=mock_engine)


@pytest.fixture
def toolkit_with_tz(mock_engine) -> SchedulerTools:
    return SchedulerTools(engine=mock_engine, default_timezone="America/New_York")


def test_schedule_job_success(toolkit: SchedulerTools, mock_engine):
    """schedule_job should create a job and return success."""
    mock_engine.add_job.return_value = CronJob(
        id="abc123def456",
        name="Daily check",
        cron_expression="0 9 * * *",
        command="check email",
        next_run=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    )
    result = toolkit.schedule_job("Daily check", "0 9 * * *", "check email")
    assert "Scheduled" in result
    assert "abc123def456" in result
    assert "Daily check" in result
    mock_engine.add_job.assert_called_once()


def test_schedule_job_uses_default_timezone(toolkit_with_tz: SchedulerTools, mock_engine):
    """schedule_job should inherit the toolkit's default timezone when none is given."""
    mock_engine.add_job.return_value = CronJob(
        id="tz123default",
        name="TZ check",
        cron_expression="0 9 * * *",
        command="check",
        timezone="America/New_York",
        next_run=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    )
    toolkit_with_tz.schedule_job("TZ check", "0 9 * * *", "check")
    called_job: CronJob = mock_engine.add_job.call_args[0][0]
    assert called_job.timezone == "America/New_York"


def test_schedule_job_explicit_timezone_overrides_default(toolkit_with_tz: SchedulerTools, mock_engine):
    """An explicit timezone arg should override the default."""
    mock_engine.add_job.return_value = CronJob(
        id="tz456override",
        name="Override TZ",
        cron_expression="0 9 * * *",
        command="check",
        timezone="Europe/London",
        next_run=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    )
    toolkit_with_tz.schedule_job("Override TZ", "0 9 * * *", "check", timezone="Europe/London")
    called_job: CronJob = mock_engine.add_job.call_args[0][0]
    assert called_job.timezone == "Europe/London"


def test_schedule_job_invalid_cron(toolkit: SchedulerTools, mock_engine):
    """schedule_job should reject invalid cron expressions."""
    result = toolkit.schedule_job("Bad", "not valid", "nope")
    assert "Invalid cron" in result
    mock_engine.add_job.assert_not_called()


def test_schedule_job_engine_error(toolkit: SchedulerTools, mock_engine):
    """schedule_job should handle engine errors gracefully."""
    mock_engine.add_job.side_effect = RuntimeError("Scheduler down")
    result = toolkit.schedule_job("Fail", "0 * * * *", "test")
    assert "Failed" in result


def test_list_scheduled_jobs_empty(toolkit: SchedulerTools, mock_engine):
    """list_scheduled_jobs should report when no jobs exist."""
    mock_engine.list_jobs.return_value = []
    result = toolkit.list_scheduled_jobs()
    assert "No scheduled jobs" in result


def test_list_scheduled_jobs_with_data(toolkit: SchedulerTools, mock_engine):
    """list_scheduled_jobs should format jobs nicely."""
    mock_engine.list_jobs.return_value = [
        CronJob(
            id="aaa111222333",
            name="Job A",
            cron_expression="0 * * * *",
            command="do A",
            run_count=5,
            last_run=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            next_run=datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc),
        ),
        CronJob(
            id="bbb444555666",
            name="Job B",
            cron_expression="*/30 * * * *",
            command="do B",
            enabled=False,
        ),
    ]
    result = toolkit.list_scheduled_jobs()
    assert "Job A" in result
    assert "Job B" in result
    assert "paused" in result
    assert "enabled" in result


def test_get_job_details_found(toolkit: SchedulerTools, mock_engine):
    """get_job_details should return formatted job info."""
    mock_engine.get_job.return_value = CronJob(
        id="detail123456",
        name="Detailed Job",
        cron_expression="0 9 * * 1",
        command="weekly task",
        job_type=JobType.USER,
        run_count=10,
        created_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    result = toolkit.get_job_details("detail123456")
    assert "Detailed Job" in result
    assert "detail123456" in result
    assert "weekly task" in result
    assert "user" in result


def test_get_job_details_not_found(toolkit: SchedulerTools, mock_engine):
    """get_job_details should report if job doesn't exist."""
    mock_engine.get_job.return_value = None
    result = toolkit.get_job_details("nope")
    assert "not found" in result


def test_pause_scheduled_job(toolkit: SchedulerTools, mock_engine):
    """pause_scheduled_job should return success."""
    mock_engine.pause_job.return_value = CronJob(
        id="pause1234567",
        name="Paused",
        cron_expression="0 * * * *",
        command="wait",
        enabled=False,
    )
    result = toolkit.pause_scheduled_job("pause1234567")
    assert "Paused" in result
    mock_engine.pause_job.assert_called_once_with("pause1234567")


def test_pause_scheduled_job_not_found(toolkit: SchedulerTools, mock_engine):
    """pause_scheduled_job should report if job doesn't exist."""
    mock_engine.pause_job.return_value = None
    result = toolkit.pause_scheduled_job("nope")
    assert "not found" in result


def test_resume_scheduled_job(toolkit: SchedulerTools, mock_engine):
    """resume_scheduled_job should return success with next run."""
    mock_engine.resume_job.return_value = CronJob(
        id="resu12345678",
        name="Resumed",
        cron_expression="0 * * * *",
        command="go",
        enabled=True,
        next_run=datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc),
    )
    result = toolkit.resume_scheduled_job("resu12345678")
    assert "Resumed" in result
    mock_engine.resume_job.assert_called_once_with("resu12345678")


def test_delete_scheduled_job(toolkit: SchedulerTools, mock_engine):
    """delete_scheduled_job should return success."""
    mock_engine.remove_job.return_value = True
    result = toolkit.delete_scheduled_job("del123456789")
    assert "Deleted" in result


def test_delete_scheduled_job_not_found(toolkit: SchedulerTools, mock_engine):
    """delete_scheduled_job should report if job doesn't exist."""
    mock_engine.remove_job.return_value = False
    result = toolkit.delete_scheduled_job("nope")
    assert "not found" in result
