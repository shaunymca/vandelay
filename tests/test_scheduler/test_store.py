"""Tests for CronJobStore JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vandelay.scheduler.models import CronJob, JobType
from vandelay.scheduler.store import CronJobStore


@pytest.fixture
def store(tmp_path: Path) -> CronJobStore:
    return CronJobStore(path=tmp_path / "cron_jobs.json")


@pytest.fixture
def sample_job() -> CronJob:
    return CronJob(
        id="abcdef123456",
        name="Test Job",
        cron_expression="*/5 * * * *",
        command="say hello",
    )


def test_empty_store(store: CronJobStore):
    """A new store with no file should be empty."""
    assert store.all() == []


def test_add_and_get(store: CronJobStore, sample_job: CronJob):
    """Adding a job should make it retrievable."""
    store.add(sample_job)
    assert store.get("abcdef123456") is not None
    assert store.get("abcdef123456").name == "Test Job"


def test_get_nonexistent(store: CronJobStore):
    """Getting a nonexistent ID should return None."""
    assert store.get("doesnotexist") is None


def test_add_persists_to_disk(store: CronJobStore, sample_job: CronJob):
    """Adding a job should write it to the JSON file."""
    store.add(sample_job)
    data = json.loads(store._path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["id"] == "abcdef123456"


def test_load_from_disk(tmp_path: Path, sample_job: CronJob):
    """A new store should pick up jobs from an existing file."""
    path = tmp_path / "cron_jobs.json"
    store1 = CronJobStore(path=path)
    store1.add(sample_job)

    # Create a fresh store from the same path
    store2 = CronJobStore(path=path)
    assert len(store2.all()) == 1
    assert store2.get("abcdef123456").name == "Test Job"


def test_update_job(store: CronJobStore, sample_job: CronJob):
    """Updating a job should persist the changes."""
    store.add(sample_job)
    sample_job.enabled = False
    sample_job.run_count = 3
    store.update(sample_job)

    # Reload from disk
    store2 = CronJobStore(path=store._path)
    job = store2.get("abcdef123456")
    assert job.enabled is False
    assert job.run_count == 3


def test_remove_job(store: CronJobStore, sample_job: CronJob):
    """Removing a job should delete it from store and disk."""
    store.add(sample_job)
    assert store.remove("abcdef123456") is True
    assert store.get("abcdef123456") is None
    assert store.all() == []


def test_remove_nonexistent(store: CronJobStore):
    """Removing a nonexistent job should return False."""
    assert store.remove("nope") is False


def test_all_returns_list(store: CronJobStore):
    """all() should return a list of all jobs."""
    store.add(CronJob(id="aaa111222333", name="A", cron_expression="* * * * *", command="a"))
    store.add(CronJob(id="bbb444555666", name="B", cron_expression="* * * * *", command="b"))
    assert len(store.all()) == 2


def test_find_by_type(store: CronJobStore):
    """find_by_type should filter jobs by JobType."""
    store.add(CronJob(id="usr123456789", name="User Job", cron_expression="* * * * *",
                       command="u", job_type=JobType.USER))
    store.add(CronJob(id="hbt123456789", name="Heartbeat", cron_expression="* * * * *",
                       command="h", job_type=JobType.HEARTBEAT))
    store.add(CronJob(id="sys123456789", name="System", cron_expression="* * * * *",
                       command="s", job_type=JobType.SYSTEM))

    assert len(store.find_by_type(JobType.USER)) == 1
    assert len(store.find_by_type(JobType.HEARTBEAT)) == 1
    assert len(store.find_by_type(JobType.SYSTEM)) == 1


def test_atomic_write(store: CronJobStore, sample_job: CronJob):
    """No .tmp file should remain after save."""
    store.add(sample_job)
    tmp_file = store._path.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_corrupted_file(tmp_path: Path):
    """Store should handle a corrupted JSON file gracefully."""
    path = tmp_path / "cron_jobs.json"
    path.write_text("NOT VALID JSON{{{", encoding="utf-8")
    store = CronJobStore(path=path)
    assert store.all() == []
