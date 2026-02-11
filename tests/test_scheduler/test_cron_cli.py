"""Tests for the cron CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vandelay.cli.cron_commands import app
from vandelay.scheduler.models import CronJob
from vandelay.scheduler.store import CronJobStore

runner = CliRunner()


@pytest.fixture
def store(tmp_path: Path) -> CronJobStore:
    return CronJobStore(path=tmp_path / "cron_jobs.json")


@pytest.fixture(autouse=True)
def patch_store(store):
    """Patch _get_store to use our tmp_path store."""
    with patch("vandelay.cli.cron_commands._get_store", return_value=store):
        yield


def test_list_empty(store):
    """List with no jobs should show a help message."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No cron jobs" in result.output


def test_add_and_list(store):
    """Adding a job should make it appear in list."""
    result = runner.invoke(app, ["add", "Test Job", "*/5 * * * *", "say hello"])
    assert result.exit_code == 0
    assert "Added job" in result.output
    assert "Test Job" in result.output

    # Now list
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Test Job" in result.output
    assert "*/5 * * * *" in result.output


def test_add_invalid_cron():
    """Adding with an invalid cron expression should fail."""
    result = runner.invoke(app, ["add", "Bad", "not valid", "nope"])
    assert result.exit_code == 1
    assert "Invalid cron" in result.output


def test_remove_job(store):
    """Removing a job should delete it."""
    job = CronJob(id="rmtest123456", name="Remove Me",
                  cron_expression="0 * * * *", command="bye")
    store.add(job)

    result = runner.invoke(app, ["remove", "rmtest123456"])
    assert result.exit_code == 0
    assert "Removed" in result.output
    assert store.get("rmtest123456") is None


def test_remove_nonexistent():
    """Removing a nonexistent job should fail."""
    result = runner.invoke(app, ["remove", "doesnotexist"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_pause_job(store):
    """Pausing a job should set it to disabled."""
    job = CronJob(id="ptest1234567", name="Pause Me",
                  cron_expression="0 * * * *", command="wait")
    store.add(job)

    result = runner.invoke(app, ["pause", "ptest1234567"])
    assert result.exit_code == 0
    assert "Paused" in result.output
    assert store.get("ptest1234567").enabled is False


def test_pause_already_paused(store):
    """Pausing an already-paused job should report it."""
    job = CronJob(id="ptest2345678", name="Already Paused",
                  cron_expression="0 * * * *", command="wait", enabled=False)
    store.add(job)

    result = runner.invoke(app, ["pause", "ptest2345678"])
    assert result.exit_code == 0
    assert "already paused" in result.output


def test_resume_job(store):
    """Resuming a paused job should re-enable it."""
    job = CronJob(id="rtest1234567", name="Resume Me",
                  cron_expression="0 * * * *", command="go", enabled=False)
    store.add(job)

    result = runner.invoke(app, ["resume", "rtest1234567"])
    assert result.exit_code == 0
    assert "Resumed" in result.output
    assert store.get("rtest1234567").enabled is True
