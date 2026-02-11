"""Tests for scheduler models."""

from __future__ import annotations

from datetime import datetime, timezone

from vandelay.scheduler.models import CronJob, JobType, _generate_id


def test_generate_id_length():
    """Generated IDs should be 12-char hex strings."""
    id_ = _generate_id()
    assert len(id_) == 12
    assert all(c in "0123456789abcdef" for c in id_)


def test_generate_id_unique():
    """IDs should be unique across calls."""
    ids = {_generate_id() for _ in range(100)}
    assert len(ids) == 100


def test_cron_job_defaults():
    """CronJob should have sensible defaults."""
    job = CronJob(name="Test", cron_expression="*/5 * * * *", command="hello")
    assert len(job.id) == 12
    assert job.job_type == JobType.USER
    assert job.enabled is True
    assert job.timezone == "UTC"
    assert job.run_count == 0
    assert job.last_run is None
    assert job.last_result is None


def test_cron_job_custom_fields():
    """CronJob should accept custom values."""
    job = CronJob(
        id="custom123456",
        name="Custom",
        cron_expression="0 9 * * 1",
        command="weekly report",
        job_type=JobType.SYSTEM,
        enabled=False,
        timezone="US/Eastern",
    )
    assert job.id == "custom123456"
    assert job.job_type == JobType.SYSTEM
    assert job.enabled is False
    assert job.timezone == "US/Eastern"


def test_cron_job_created_at_is_utc():
    """created_at should default to a UTC timestamp."""
    job = CronJob(name="Test", cron_expression="* * * * *", command="ping")
    assert job.created_at.tzinfo is not None


def test_cron_job_serialization_roundtrip():
    """CronJob should serialize and deserialize cleanly."""
    job = CronJob(name="Roundtrip", cron_expression="0 * * * *", command="check")
    data = job.model_dump(mode="json")
    restored = CronJob.model_validate(data)
    assert restored.id == job.id
    assert restored.name == job.name
    assert restored.cron_expression == job.cron_expression
    assert restored.command == job.command


def test_job_type_values():
    """JobType enum should have the expected string values."""
    assert JobType.USER == "user"
    assert JobType.HEARTBEAT == "heartbeat"
    assert JobType.SYSTEM == "system"


def test_cron_job_with_last_run():
    """CronJob should store last_run and run_count."""
    now = datetime.now(timezone.utc)
    job = CronJob(
        name="Ran",
        cron_expression="* * * * *",
        command="test",
        last_run=now,
        run_count=5,
        last_result="HEARTBEAT_OK",
    )
    assert job.last_run == now
    assert job.run_count == 5
    assert job.last_result == "HEARTBEAT_OK"
