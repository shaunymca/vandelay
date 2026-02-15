"""Tests for TaskQueueTools toolkit."""

from __future__ import annotations

from pathlib import Path

import pytest

from vandelay.tasks.models import AgentTask, TaskStatus
from vandelay.tasks.store import TaskStore
from vandelay.tools.tasks import TaskQueueTools


@pytest.fixture
def store(tmp_path: Path) -> TaskStore:
    return TaskStore(path=tmp_path / "task_queue.json")


@pytest.fixture
def tools(store: TaskStore) -> TaskQueueTools:
    return TaskQueueTools(store=store)


class TestCreateTask:
    def test_basic_create(self, tools: TaskQueueTools, store: TaskStore):
        result = tools.create_task("Set up Calendar")
        assert "Created task" in result
        assert "Set up Calendar" in result
        assert len(store.all()) == 1

    def test_create_with_priority(self, tools: TaskQueueTools, store: TaskStore):
        result = tools.create_task("Urgent fix", priority=2)
        assert "urgent" in result
        task = store.all()[0]
        assert task.priority == 2

    def test_create_with_owner(self, tools: TaskQueueTools, store: TaskStore):
        result = tools.create_task("Research pricing", owner="browser")
        assert "browser" in result
        task = store.all()[0]
        assert task.owner == "browser"

    def test_create_with_due_at(self, tools: TaskQueueTools, store: TaskStore):
        result = tools.create_task("Review PR", due_at="2025-06-15T09:00:00")
        assert "Due:" in result
        task = store.all()[0]
        assert task.due_at is not None

    def test_create_invalid_due_at(self, tools: TaskQueueTools):
        result = tools.create_task("Bad date", due_at="not-a-date")
        assert "Invalid due_at format" in result


class TestListTasks:
    def test_empty_list(self, tools: TaskQueueTools):
        result = tools.list_tasks()
        assert "No tasks" in result

    def test_list_all(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task A"))
        store.add(AgentTask(id="t2", title="Task B"))
        result = tools.list_tasks()
        assert "Task A" in result
        assert "Task B" in result

    def test_filter_by_status(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Pending", status=TaskStatus.PENDING))
        store.add(AgentTask(id="t2", title="Done", status=TaskStatus.COMPLETED))
        result = tools.list_tasks(status_filter="completed")
        assert "Done" in result
        assert "Pending" not in result

    def test_filter_by_owner(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Mine", owner="browser"))
        store.add(AgentTask(id="t2", title="Theirs", owner="system"))
        result = tools.list_tasks(owner_filter="browser")
        assert "Mine" in result
        assert "Theirs" not in result

    def test_invalid_status_filter(self, tools: TaskQueueTools):
        result = tools.list_tasks(status_filter="bogus")
        assert "Invalid status filter" in result


class TestGetTask:
    def test_get_existing(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Test Task", description="Details here"))
        result = tools.get_task("t1")
        assert "Test Task" in result
        assert "Details here" in result

    def test_get_nonexistent(self, tools: TaskQueueTools):
        result = tools.get_task("nope")
        assert "not found" in result


class TestUpdateTask:
    def test_update_status(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task"))
        result = tools.update_task("t1", status="in_progress")
        assert "in_progress" in result
        assert store.get("t1").status == TaskStatus.IN_PROGRESS
        assert store.get("t1").started_at is not None

    def test_update_owner(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task"))
        result = tools.update_task("t1", owner="browser")
        assert "browser" in result
        assert store.get("t1").owner == "browser"

    def test_update_nonexistent(self, tools: TaskQueueTools):
        result = tools.update_task("nope", status="completed")
        assert "not found" in result

    def test_update_invalid_status(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task"))
        result = tools.update_task("t1", status="bogus")
        assert "Invalid status" in result

    def test_no_changes(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task"))
        result = tools.update_task("t1")
        assert "No changes" in result


class TestCompleteTask:
    def test_complete(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task"))
        result = tools.complete_task("t1", result="All done")
        assert "Completed" in result
        task = store.get("t1")
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == "All done"

    def test_complete_nonexistent(self, tools: TaskQueueTools):
        result = tools.complete_task("nope")
        assert "not found" in result


class TestCancelTask:
    def test_cancel(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task"))
        result = tools.cancel_task("t1", reason="No longer needed")
        assert "Cancelled" in result
        task = store.get("t1")
        assert task.status == TaskStatus.CANCELLED
        assert task.result == "No longer needed"

    def test_cancel_nonexistent(self, tools: TaskQueueTools):
        result = tools.cancel_task("nope")
        assert "not found" in result


class TestCheckOpenTasks:
    def test_no_open(self, tools: TaskQueueTools):
        result = tools.check_open_tasks()
        assert "No open tasks" in result

    def test_returns_open_tasks(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Pending Task", priority=0))
        store.add(AgentTask(id="t2", title="Urgent Task", priority=2))
        store.add(AgentTask(id="t3", title="Done", status=TaskStatus.COMPLETED))

        result = tools.check_open_tasks()
        assert "Urgent Task" in result
        assert "Pending Task" in result
        assert "Done" not in result
        # Urgent should appear before pending (priority sorting)
        assert result.index("Urgent Task") < result.index("Pending Task")

    def test_includes_description(self, tools: TaskQueueTools, store: TaskStore):
        store.add(AgentTask(id="t1", title="Task", description="Step-by-step instructions"))
        result = tools.check_open_tasks()
        assert "Step-by-step instructions" in result
