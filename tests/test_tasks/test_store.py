"""Tests for TaskStore JSON persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vandelay.tasks.models import AgentTask, TaskStatus
from vandelay.tasks.store import TaskStore


@pytest.fixture
def store(tmp_path: Path) -> TaskStore:
    return TaskStore(path=tmp_path / "task_queue.json")


@pytest.fixture
def sample_task() -> AgentTask:
    return AgentTask(
        id="abcdef123456",
        title="Set up Google Calendar",
        description="Connect the Google Calendar API and test event creation",
        priority=1,
    )


def test_empty_store(store: TaskStore):
    """A new store with no file should be empty."""
    assert store.all() == []


def test_add_and_get(store: TaskStore, sample_task: AgentTask):
    """Adding a task should make it retrievable."""
    store.add(sample_task)
    assert store.get("abcdef123456") is not None
    assert store.get("abcdef123456").title == "Set up Google Calendar"


def test_get_nonexistent(store: TaskStore):
    """Getting a nonexistent ID should return None."""
    assert store.get("doesnotexist") is None


def test_add_persists_to_disk(store: TaskStore, sample_task: AgentTask):
    """Adding a task should write it to the JSON file."""
    store.add(sample_task)
    data = json.loads(store._path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["id"] == "abcdef123456"


def test_load_from_disk(tmp_path: Path, sample_task: AgentTask):
    """A new store should pick up tasks from an existing file."""
    path = tmp_path / "task_queue.json"
    store1 = TaskStore(path=path)
    store1.add(sample_task)

    store2 = TaskStore(path=path)
    assert len(store2.all()) == 1
    assert store2.get("abcdef123456").title == "Set up Google Calendar"


def test_update_task(store: TaskStore, sample_task: AgentTask):
    """Updating a task should persist the changes."""
    store.add(sample_task)
    sample_task.status = TaskStatus.IN_PROGRESS
    sample_task.started_at = datetime.now(UTC)
    store.update(sample_task)

    store2 = TaskStore(path=store._path)
    task = store2.get("abcdef123456")
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.started_at is not None


def test_remove_task(store: TaskStore, sample_task: AgentTask):
    """Removing a task should delete it from store and disk."""
    store.add(sample_task)
    assert store.remove("abcdef123456") is True
    assert store.get("abcdef123456") is None
    assert store.all() == []


def test_remove_nonexistent(store: TaskStore):
    """Removing a nonexistent task should return False."""
    assert store.remove("nope") is False


def test_all_returns_list(store: TaskStore):
    """all() should return a list of all tasks."""
    store.add(AgentTask(id="aaa111222333", title="Task A"))
    store.add(AgentTask(id="bbb444555666", title="Task B"))
    assert len(store.all()) == 2


def test_find_open(store: TaskStore):
    """find_open() should return pending and in_progress tasks."""
    store.add(AgentTask(id="t1", title="Pending", status=TaskStatus.PENDING))
    store.add(AgentTask(id="t2", title="In Progress", status=TaskStatus.IN_PROGRESS))
    store.add(AgentTask(id="t3", title="Completed", status=TaskStatus.COMPLETED))
    store.add(AgentTask(id="t4", title="Failed", status=TaskStatus.FAILED))
    store.add(AgentTask(id="t5", title="Cancelled", status=TaskStatus.CANCELLED))

    open_tasks = store.find_open()
    assert len(open_tasks) == 2
    ids = {t.id for t in open_tasks}
    assert ids == {"t1", "t2"}


def test_find_open_priority_sorting(store: TaskStore):
    """find_open() should sort by priority desc, then created_at asc."""
    now = datetime.now(UTC)
    store.add(AgentTask(
        id="low", title="Low priority", priority=0,
        created_at=now,
    ))
    store.add(AgentTask(
        id="urgent", title="Urgent", priority=2,
        created_at=now,
    ))
    store.add(AgentTask(
        id="high", title="High priority", priority=1,
        created_at=now,
    ))

    tasks = store.find_open()
    assert [t.id for t in tasks] == ["urgent", "high", "low"]


def test_find_by_owner(store: TaskStore):
    """find_by_owner() should filter tasks by owner."""
    store.add(AgentTask(id="t1", title="Task 1", owner="browser"))
    store.add(AgentTask(id="t2", title="Task 2", owner="system"))
    store.add(AgentTask(id="t3", title="Task 3", owner="browser"))

    browser_tasks = store.find_by_owner("browser")
    assert len(browser_tasks) == 2
    assert all(t.owner == "browser" for t in browser_tasks)


def test_find_by_status(store: TaskStore):
    """find_by_status() should filter tasks by status."""
    store.add(AgentTask(id="t1", title="Task 1", status=TaskStatus.PENDING))
    store.add(AgentTask(id="t2", title="Task 2", status=TaskStatus.COMPLETED))
    store.add(AgentTask(id="t3", title="Task 3", status=TaskStatus.PENDING))

    pending = store.find_by_status(TaskStatus.PENDING)
    assert len(pending) == 2


def test_atomic_write(store: TaskStore, sample_task: AgentTask):
    """No .tmp file should remain after save."""
    store.add(sample_task)
    tmp_file = store._path.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_corrupted_file(tmp_path: Path):
    """Store should handle a corrupted JSON file gracefully."""
    path = tmp_path / "task_queue.json"
    path.write_text("NOT VALID JSON{{{", encoding="utf-8")
    store = TaskStore(path=path)
    assert store.all() == []
