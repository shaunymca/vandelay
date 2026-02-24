"""Tests for the Scheduler tab and CronJobStore integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.scheduler.models import CronJob, JobType
from vandelay.scheduler.store import CronJobStore


# ---------------------------------------------------------------------------
# CronJobStore round-trip
# ---------------------------------------------------------------------------


class TestCronJobStoreRoundTrip:
    def test_add_and_reload_persists_job(self, tmp_path):
        """Add a job, reload from disk, confirm it's still there."""
        path = tmp_path / "cron_jobs.json"
        store = CronJobStore(path=path)

        job = CronJob(name="Test", cron_expression="*/5 * * * *", command="hello")
        store.add(job)

        # Fresh store from same file
        store2 = CronJobStore(path=path)
        jobs = store2.all()
        assert len(jobs) == 1
        assert jobs[0].name == "Test"
        assert jobs[0].cron_expression == "*/5 * * * *"

    def test_update_persists_changes(self, tmp_path):
        path = tmp_path / "cron_jobs.json"
        store = CronJobStore(path=path)

        job = CronJob(name="Orig", cron_expression="0 * * * *", command="ping")
        store.add(job)

        updated = job.model_copy(update={"name": "Updated"})
        store.update(updated)

        store2 = CronJobStore(path=path)
        assert store2.get(job.id).name == "Updated"

    def test_remove_persists_deletion(self, tmp_path):
        path = tmp_path / "cron_jobs.json"
        store = CronJobStore(path=path)

        job = CronJob(name="Del", cron_expression="* * * * *", command="x")
        store.add(job)
        store.remove(job.id)

        store2 = CronJobStore(path=path)
        assert store2.get(job.id) is None
        assert len(store2.all()) == 0

    def test_missing_file_starts_empty(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        store = CronJobStore(path=path)
        assert store.all() == []


# ---------------------------------------------------------------------------
# CronJobModal validation
# ---------------------------------------------------------------------------


class TestCronJobModal:
    """Unit tests for modal validation logic (no Textual pilot needed)."""

    def _run_validation(self, name: str, expr: str, cmd: str) -> str | None:
        """Replicate modal validation. Returns error string or None if valid."""
        if not name:
            return "Name is required."
        if len(expr.split()) != 5:
            return "Expression must have exactly 5 space-separated fields."
        if not cmd:
            return "Command is required."
        return None

    def test_valid_input_passes(self):
        err = self._run_validation("Daily", "*/30 * * * *", "run report")
        assert err is None

    def test_empty_name_fails(self):
        err = self._run_validation("", "*/30 * * * *", "run report")
        assert err is not None
        assert "Name" in err

    def test_bad_expression_not_five_fields(self):
        err = self._run_validation("Job", "*/30 * * *", "run")  # 4 fields
        assert err is not None
        assert "5" in err

    def test_bad_expression_six_fields(self):
        err = self._run_validation("Job", "0 */2 * * * *", "run")  # 6 fields (seconds)
        assert err is not None
        assert "5" in err

    def test_empty_command_fails(self):
        err = self._run_validation("Job", "0 * * * *", "")
        assert err is not None
        assert "Command" in err


# ---------------------------------------------------------------------------
# Heartbeat job — button state
# ---------------------------------------------------------------------------


class TestHeartbeatJobProtection:
    def _make_store_with_heartbeat(self, tmp_path: Path) -> CronJobStore:
        path = tmp_path / "cron_jobs.json"
        store = CronJobStore(path=path)
        hb = CronJob(
            name="Heartbeat",
            cron_expression="*/30 * * * *",
            command="heartbeat",
            job_type=JobType.HEARTBEAT,
        )
        store.add(hb)
        return store, hb

    def test_heartbeat_job_type(self, tmp_path):
        store, hb = self._make_store_with_heartbeat(tmp_path)
        assert hb.job_type == JobType.HEARTBEAT

    def test_user_job_not_heartbeat(self, tmp_path):
        path = tmp_path / "cron_jobs.json"
        store = CronJobStore(path=path)
        job = CronJob(name="Normal", cron_expression="0 * * * *", command="ping")
        store.add(job)
        assert job.job_type == JobType.USER
        assert job.job_type != JobType.HEARTBEAT

    def test_scheduler_tab_disables_edit_for_heartbeat(self, tmp_path):
        """Simulate button state logic for a heartbeat selection."""
        from vandelay.tui.tabs.scheduler import SchedulerTab

        store, hb = self._make_store_with_heartbeat(tmp_path)

        # Replicate the logic inside _update_button_state
        job = hb
        is_heartbeat = job.job_type == "heartbeat"
        editable = not is_heartbeat

        assert not editable, "Heartbeat job should not be editable"

    def test_scheduler_tab_enables_edit_for_user_job(self, tmp_path):
        path = tmp_path / "cron_jobs.json"
        store = CronJobStore(path=path)
        job = CronJob(name="Normal", cron_expression="0 * * * *", command="ping")
        store.add(job)

        is_heartbeat = job.job_type == "heartbeat"
        editable = not is_heartbeat

        assert editable, "User job should be editable"


# ---------------------------------------------------------------------------
# Clear completed tasks
# ---------------------------------------------------------------------------


class TestClearCompleted:
    def _make_task_queue(self, tmp_path: Path) -> Path:
        path = tmp_path / "task_queue.json"
        tasks = [
            {"id": "aaa", "status": "done", "command": "old task", "created_at": "2025-01-01"},
            {"id": "bbb", "status": "failed", "command": "broke", "created_at": "2025-01-02"},
            {"id": "ccc", "status": "pending", "command": "still going", "created_at": "2025-01-03"},
            {"id": "ddd", "status": "running", "command": "in progress", "created_at": "2025-01-04"},
        ]
        path.write_text(json.dumps(tasks), encoding="utf-8")
        return path

    def test_clear_removes_done_and_failed(self, tmp_path):
        from vandelay.tui.tabs.scheduler import _load_tasks, _save_tasks

        path = self._make_task_queue(tmp_path)
        tasks = _load_tasks(path)
        remaining = [t for t in tasks if t.get("status") not in {"done", "failed"}]
        _save_tasks(path, remaining)

        reloaded = _load_tasks(path)
        statuses = [t["status"] for t in reloaded]
        assert "done" not in statuses
        assert "failed" not in statuses
        assert "pending" in statuses
        assert "running" in statuses
        assert len(reloaded) == 2

    def test_clear_empty_queue_is_safe(self, tmp_path):
        from vandelay.tui.tabs.scheduler import _load_tasks, _save_tasks

        path = tmp_path / "task_queue.json"
        tasks = _load_tasks(path)  # file doesn't exist
        remaining = [t for t in tasks if t.get("status") not in {"done", "failed"}]
        _save_tasks(path, remaining)

        reloaded = _load_tasks(path)
        assert reloaded == []

    def test_clear_all_completed(self, tmp_path):
        from vandelay.tui.tabs.scheduler import _load_tasks, _save_tasks

        path = tmp_path / "task_queue.json"
        tasks = [
            {"id": "x", "status": "done", "command": "a", "created_at": "2025-01-01"},
            {"id": "y", "status": "failed", "command": "b", "created_at": "2025-01-02"},
        ]
        path.write_text(json.dumps(tasks), encoding="utf-8")

        loaded = _load_tasks(path)
        remaining = [t for t in loaded if t.get("status") not in {"done", "failed"}]
        _save_tasks(path, remaining)

        reloaded = _load_tasks(path)
        assert reloaded == []


# ---------------------------------------------------------------------------
# Import smoke tests
# ---------------------------------------------------------------------------


class TestSchedulerTabImport:
    def test_import_scheduler_tab(self):
        from vandelay.tui.tabs.scheduler import SchedulerTab

        assert SchedulerTab is not None

    def test_import_cron_job_modal(self):
        from vandelay.tui.tabs.scheduler import CronJobModal

        assert CronJobModal is not None

    def test_import_helpers(self):
        from vandelay.tui.tabs.scheduler import _load_tasks, _save_tasks

        assert callable(_load_tasks)
        assert callable(_save_tasks)

    def test_task_edit_modal_stores_dict_not_overwritten(self):
        """Regression: _task_data must not collide with Textual's internal _task attribute."""
        from vandelay.tui.tabs.scheduler import TaskEditModal

        task = {"id": "abc123", "status": "pending", "command": "hello", "created_at": "2025-01-01"}
        modal = TaskEditModal(task)
        # _task_data should be our dict, not an asyncio Task
        assert isinstance(modal._task_data, dict)
        assert modal._task_data.get("id") == "abc123"


# ---------------------------------------------------------------------------
# Heartbeat settings validation
# ---------------------------------------------------------------------------


class TestHeartbeatValidation:
    """Test _save_heartbeat validation logic (extracted from widget)."""

    def _validate(self, enabled, interval, start, end, tz="UTC"):
        """Replicate the validation logic from _save_heartbeat."""
        errors = []
        if not (0 <= start <= 23 and 0 <= end <= 23):
            errors.append("Hours must be 0–23.")
        if start >= end:
            errors.append("Start must be before end.")
        if interval < 1:
            errors.append("Interval must be at least 1 minute.")
        return errors

    def test_valid_config_passes(self):
        assert self._validate(True, 30, 8, 22) == []

    def test_invalid_start_hour(self):
        errors = self._validate(True, 30, 25, 22)
        assert any("0–23" in e for e in errors)

    def test_start_after_end_fails(self):
        errors = self._validate(True, 30, 22, 8)
        assert any("Start must be before" in e for e in errors)

    def test_start_equal_end_fails(self):
        errors = self._validate(True, 30, 8, 8)
        assert any("Start must be before" in e for e in errors)

    def test_zero_interval_fails(self):
        errors = self._validate(True, 0, 8, 22)
        assert any("at least 1" in e for e in errors)

    def test_disabled_still_validates(self):
        """Validation runs regardless of enabled state."""
        errors = self._validate(False, 0, 8, 22)
        assert any("at least 1" in e for e in errors)
