"""Agent-facing toolkit for managing the persistent task queue."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from agno.tools import Toolkit

from vandelay.tasks.models import AgentTask, TaskStatus

if TYPE_CHECKING:
    from vandelay.tasks.store import TaskStore

logger = logging.getLogger("vandelay.tools.tasks")


class TaskQueueTools(Toolkit):
    """Lets the agent create, track, and complete persistent tasks."""

    def __init__(self, store: TaskStore) -> None:
        super().__init__(name="task_queue")
        self._store = store

        self.register(self.create_task)
        self.register(self.list_tasks)
        self.register(self.get_task)
        self.register(self.update_task)
        self.register(self.complete_task)
        self.register(self.cancel_task)
        self.register(self.check_open_tasks)

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: int = 0,
        owner: str = "",
        due_at: str = "",
    ) -> str:
        """Create a new task in the persistent task queue.

        Tasks survive restarts and are picked up automatically on heartbeat.
        Use this when you need to track work that spans sessions.

        Args:
            title: Short description of the task (e.g. "Set up Google Calendar").
            description: Detailed instructions for completing the task.
            priority: 0=normal, 1=high, 2=urgent. Higher priority tasks are picked up first.
            owner: Team member name to assign to, or empty for self/unassigned.
            due_at: Optional due date in ISO format (e.g. "2025-01-15T09:00:00").

        Returns:
            str: Success message with task ID.
        """
        parsed_due: datetime | None = None
        if due_at:
            try:
                parsed_due = datetime.fromisoformat(due_at)
                if parsed_due.tzinfo is None:
                    parsed_due = parsed_due.replace(tzinfo=UTC)
            except ValueError:
                return f"Invalid due_at format: '{due_at}'. Use ISO format (YYYY-MM-DDTHH:MM:SS)."

        task = AgentTask(
            title=title,
            description=description,
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
            priority=priority,
            owner=owner,
            due_at=parsed_due,
        )
        self._store.add(task)

        priority_label = {0: "normal", 1: "high", 2: "urgent"}.get(priority, str(priority))
        parts = [f"Created task '{task.title}' (ID: {task.id}, priority: {priority_label})"]
        if owner:
            parts.append(f"Assigned to: {owner}")
        if parsed_due:
            parts.append(f"Due: {parsed_due.strftime('%Y-%m-%d %H:%M')}")
        return ". ".join(parts) + "."

    def list_tasks(self, status_filter: str = "", owner_filter: str = "") -> str:
        """List tasks with optional filtering.

        Args:
            status_filter: Filter by status (pending, in_progress, completed, failed, cancelled).
            owner_filter: Filter by owner name.

        Returns:
            str: Formatted list of tasks, or a message if none match.
        """
        tasks = self._store.all()

        if status_filter:
            try:
                status = TaskStatus(status_filter)
                tasks = [t for t in tasks if t.status == status]
            except ValueError:
                return (
                    f"Invalid status filter: '{status_filter}'. "
                    f"Valid: {', '.join(s.value for s in TaskStatus)}."
                )

        if owner_filter:
            tasks = [t for t in tasks if t.owner == owner_filter]

        if not tasks:
            filters = []
            if status_filter:
                filters.append(f"status={status_filter}")
            if owner_filter:
                filters.append(f"owner={owner_filter}")
            suffix = f" matching {', '.join(filters)}" if filters else ""
            return f"No tasks{suffix}."

        lines = ["# Tasks\n"]
        for task in tasks:
            priority_marker = {1: " [HIGH]", 2: " [URGENT]"}.get(task.priority, "")
            owner_info = f" → {task.owner}" if task.owner else ""
            due_info = f" | Due: {task.due_at.strftime('%Y-%m-%d %H:%M')}" if task.due_at else ""
            lines.append(
                f"- **{task.title}** (ID: {task.id}) [{task.status.value}]{priority_marker}"
                f"{owner_info}{due_info}"
            )

        return "\n".join(lines)

    def get_task(self, task_id: str) -> str:
        """Get detailed information about a specific task.

        Args:
            task_id: The task ID to look up.

        Returns:
            str: Detailed task info, or error if not found.
        """
        task = self._store.get(task_id)
        if task is None:
            return f"Task '{task_id}' not found."

        priority_label = {0: "normal", 1: "high", 2: "urgent"}.get(
            task.priority, str(task.priority)
        )
        lines = [
            f"# Task: {task.title}",
            f"- **ID**: {task.id}",
            f"- **Status**: {task.status.value}",
            f"- **Priority**: {priority_label}",
            f"- **Owner**: {task.owner or 'unassigned'}",
            f"- **Created**: {task.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"- **Updated**: {task.updated_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        if task.description:
            lines.append(f"- **Description**: {task.description}")
        if task.due_at:
            lines.append(f"- **Due**: {task.due_at.strftime('%Y-%m-%d %H:%M')}")
        if task.started_at:
            lines.append(f"- **Started**: {task.started_at.strftime('%Y-%m-%d %H:%M')}")
        if task.completed_at:
            lines.append(f"- **Completed**: {task.completed_at.strftime('%Y-%m-%d %H:%M')}")
        if task.result:
            lines.append(f"- **Result**: {task.result[:300]}")
        if task.tags:
            lines.append(f"- **Tags**: {', '.join(task.tags)}")

        return "\n".join(lines)

    def update_task(
        self,
        task_id: str,
        status: str = "",
        result: str = "",
        owner: str = "",
    ) -> str:
        """Update a task's status, result, or owner.

        Args:
            task_id: The task ID to update.
            status: New status (pending, in_progress, completed, failed, cancelled).
            result: Result or progress note.
            owner: Reassign to a different owner.

        Returns:
            str: Success or error message.
        """
        task = self._store.get(task_id)
        if task is None:
            return f"Task '{task_id}' not found."

        now = datetime.now(UTC)
        changes: list[str] = []

        if status:
            try:
                new_status = TaskStatus(status)
            except ValueError:
                return (
                    f"Invalid status: '{status}'. "
                    f"Valid: {', '.join(s.value for s in TaskStatus)}."
                )
            task.status = new_status
            changes.append(f"status → {new_status.value}")

            if new_status == TaskStatus.IN_PROGRESS and task.started_at is None:
                task.started_at = now
            elif new_status == TaskStatus.COMPLETED:
                task.completed_at = now
            elif new_status == TaskStatus.FAILED:
                task.completed_at = now

        if result:
            task.result = result
            changes.append("result updated")

        if owner:
            task.owner = owner
            changes.append(f"owner → {owner}")

        if not changes:
            return "No changes specified."

        task.updated_at = now
        self._store.update(task)
        return f"Updated task '{task.title}' ({task.id}): {', '.join(changes)}."

    def complete_task(self, task_id: str, result: str = "") -> str:
        """Mark a task as completed with an optional result.

        Args:
            task_id: The task ID to complete.
            result: Description of the outcome.

        Returns:
            str: Success or error message.
        """
        task = self._store.get(task_id)
        if task is None:
            return f"Task '{task_id}' not found."

        now = datetime.now(UTC)
        task.status = TaskStatus.COMPLETED
        task.completed_at = now
        task.updated_at = now
        if result:
            task.result = result

        self._store.update(task)
        return f"Completed task '{task.title}' ({task.id})."

    def cancel_task(self, task_id: str, reason: str = "") -> str:
        """Cancel a task with an optional reason.

        Args:
            task_id: The task ID to cancel.
            reason: Why the task was cancelled.

        Returns:
            str: Success or error message.
        """
        task = self._store.get(task_id)
        if task is None:
            return f"Task '{task_id}' not found."

        now = datetime.now(UTC)
        task.status = TaskStatus.CANCELLED
        task.updated_at = now
        if reason:
            task.result = reason

        self._store.update(task)
        return f"Cancelled task '{task.title}' ({task.id})."

    def check_open_tasks(self) -> str:
        """Check for pending and in-progress tasks, sorted by priority.

        Call this during heartbeat to resume work after restarts.

        Returns:
            str: List of open tasks sorted by priority, or message if none.
        """
        tasks = self._store.find_open()
        if not tasks:
            return "No open tasks."

        lines = [f"# Open Tasks ({len(tasks)})\n"]
        for task in tasks:
            priority_marker = {1: " [HIGH]", 2: " [URGENT]"}.get(task.priority, "")
            owner_info = f" → {task.owner}" if task.owner else ""
            desc = f"\n  {task.description}" if task.description else ""
            lines.append(
                f"- **{task.title}** (ID: {task.id}) [{task.status.value}]"
                f"{priority_marker}{owner_info}{desc}"
            )

        return "\n".join(lines)
