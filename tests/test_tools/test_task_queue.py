"""Tests for TaskQueueTools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vandelay.tasks.models import AgentTask, TaskStatus
from vandelay.tasks.store import TaskStore
from vandelay.tools.tasks import TaskQueueTools


@pytest.fixture
def store(tmp_path: Path) -> TaskStore:
    return TaskStore(path=tmp_path / "tasks.json")


@pytest.fixture
def tools(store: TaskStore) -> TaskQueueTools:
    return TaskQueueTools(store=store)


class TestCreateTask:
    def test_creates_in_progress(self, tools: TaskQueueTools, store: TaskStore):
        """Tasks must be created as in_progress so the agent works on them immediately."""
        tools.create_task(title="Do something")
        tasks = store.all()
        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.IN_PROGRESS

    def test_started_at_set_on_create(self, tools: TaskQueueTools, store: TaskStore):
        """started_at should be populated when task is created."""
        tools.create_task(title="Do something")
        task = store.all()[0]
        assert task.started_at is not None

    def test_create_with_all_fields(self, tools: TaskQueueTools, store: TaskStore):
        tools.create_task(
            title="Deploy app",
            description="Run deploy script",
            priority=1,
            owner="cto",
        )
        task = store.all()[0]
        assert task.title == "Deploy app"
        assert task.description == "Run deploy script"
        assert task.priority == 1
        assert task.owner == "cto"
        assert task.status == TaskStatus.IN_PROGRESS

    def test_create_returns_confirmation(self, tools: TaskQueueTools):
        result = tools.create_task(title="Test task")
        assert "Test task" in result
        assert "in_progress" in result.lower() or "ID" in result


class TestCheckOpenTasks:
    def test_returns_in_progress_tasks(self, tools: TaskQueueTools, store: TaskStore):
        """check_open_tasks should include in_progress tasks (now the default)."""
        tools.create_task(title="Active work")
        result = tools.check_open_tasks()
        assert "Active work" in result

    def test_empty_queue(self, tools: TaskQueueTools):
        result = tools.check_open_tasks()
        assert "No open tasks" in result

    def test_completed_not_shown(self, tools: TaskQueueTools, store: TaskStore):
        tools.create_task(title="Done work")
        task = store.all()[0]
        tools.complete_task(task.id, result="finished")
        result = tools.check_open_tasks()
        assert "No open tasks" in result


class TestCompleteTask:
    def test_complete_marks_done(self, tools: TaskQueueTools, store: TaskStore):
        tools.create_task(title="Finish me")
        task = store.all()[0]
        tools.complete_task(task.id, result="all done")
        updated = store.get(task.id)
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == "all done"
        assert updated.completed_at is not None


class TestUpdateTask:
    def test_update_status(self, tools: TaskQueueTools, store: TaskStore):
        tools.create_task(title="Update me")
        task = store.all()[0]
        tools.update_task(task.id, status="completed")
        assert store.get(task.id).status == TaskStatus.COMPLETED

    def test_invalid_status_returns_error(self, tools: TaskQueueTools, store: TaskStore):
        tools.create_task(title="Test")
        task = store.all()[0]
        result = tools.update_task(task.id, status="running")
        assert "Invalid" in result
