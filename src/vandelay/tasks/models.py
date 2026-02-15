"""Pydantic models for the agent task queue."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """Lifecycle states for an agent task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _generate_id() -> str:
    return secrets.token_hex(6)


class AgentTask(BaseModel):
    """A single task that agents can create, track, and complete."""

    id: str = Field(default_factory=_generate_id)
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # 0=normal, 1=high, 2=urgent
    owner: str = ""  # member name or "" for unassigned
    created_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    due_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: str | None = None
    parent_id: str | None = None  # for sub-tasks (v2)
    tags: list[str] = []
