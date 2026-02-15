"""JSON file persistence for agent tasks."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from vandelay.config.constants import TASK_QUEUE_FILE
from vandelay.tasks.models import AgentTask, TaskStatus

logger = logging.getLogger("vandelay.tasks.store")


class TaskStore:
    """Load/save agent tasks from a JSON file.

    Uses atomic writes (write to .tmp, then replace) to prevent corruption.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or TASK_QUEUE_FILE
        self._tasks: dict[str, AgentTask] = {}
        self.load()

    # -- Persistence -----------------------------------------------------------

    def load(self) -> None:
        """Load tasks from disk. Silently starts empty if file is missing."""
        self._tasks.clear()
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for raw in data:
                task = AgentTask.model_validate(raw)
                self._tasks[task.id] = task
            logger.debug("Loaded %d tasks from %s", len(self._tasks), self._path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load tasks: %s", exc)

    def save(self) -> None:
        """Persist all tasks to disk atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        data = [task.model_dump(mode="json") for task in self._tasks.values()]
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(self._path)

    # -- CRUD ------------------------------------------------------------------

    def add(self, task: AgentTask) -> AgentTask:
        """Add a task and persist."""
        self._tasks[task.id] = task
        self.save()
        return task

    def get(self, task_id: str) -> AgentTask | None:
        """Retrieve a task by ID."""
        return self._tasks.get(task_id)

    def update(self, task: AgentTask) -> AgentTask:
        """Update an existing task and persist."""
        self._tasks[task.id] = task
        self.save()
        return task

    def remove(self, task_id: str) -> bool:
        """Remove a task by ID. Returns True if it existed."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self.save()
            return True
        return False

    def all(self) -> list[AgentTask]:
        """Return all tasks."""
        return list(self._tasks.values())

    # -- Query helpers ---------------------------------------------------------

    def find_open(self) -> list[AgentTask]:
        """Return pending/in_progress tasks sorted by priority desc, created_at asc."""
        open_statuses = {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}
        tasks = [t for t in self._tasks.values() if t.status in open_statuses]
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return tasks

    def find_by_owner(self, owner: str) -> list[AgentTask]:
        """Return all tasks assigned to a specific owner."""
        return [t for t in self._tasks.values() if t.owner == owner]

    def find_by_status(self, status: TaskStatus) -> list[AgentTask]:
        """Return all tasks with a given status."""
        return [t for t in self._tasks.values() if t.status == status]
