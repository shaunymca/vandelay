"""Pydantic models for scheduled jobs."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Classification of cron jobs."""

    USER = "user"
    HEARTBEAT = "heartbeat"
    SYSTEM = "system"


def _generate_id() -> str:
    return secrets.token_hex(6)


class CronJob(BaseModel):
    """A single scheduled job that sends a message to the agent."""

    id: str = Field(default_factory=_generate_id)
    name: str
    cron_expression: str  # 5-field cron (e.g. "*/30 * * * *")
    command: str  # Natural language message sent to the agent
    job_type: JobType = JobType.USER
    enabled: bool = True
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_result: Optional[str] = None
    run_count: int = 0
