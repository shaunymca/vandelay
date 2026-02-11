"""JSON file persistence for cron jobs."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from vandelay.config.constants import CRON_FILE
from vandelay.scheduler.models import CronJob, JobType

logger = logging.getLogger("vandelay.scheduler.store")


class CronJobStore:
    """Load/save cron jobs from a JSON file.

    Uses atomic writes (write to .tmp, then replace) to prevent corruption.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or CRON_FILE
        self._jobs: dict[str, CronJob] = {}
        self.load()

    # -- Persistence -----------------------------------------------------------

    def load(self) -> None:
        """Load jobs from disk. Silently starts empty if file is missing."""
        self._jobs.clear()
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for raw in data:
                job = CronJob.model_validate(raw)
                self._jobs[job.id] = job
            logger.debug("Loaded %d cron jobs from %s", len(self._jobs), self._path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load cron jobs: %s", exc)

    def save(self) -> None:
        """Persist all jobs to disk atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        data = [job.model_dump(mode="json") for job in self._jobs.values()]
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(self._path)

    # -- CRUD ------------------------------------------------------------------

    def add(self, job: CronJob) -> CronJob:
        """Add a job and persist."""
        self._jobs[job.id] = job
        self.save()
        return job

    def get(self, job_id: str) -> Optional[CronJob]:
        """Retrieve a job by ID."""
        return self._jobs.get(job_id)

    def update(self, job: CronJob) -> CronJob:
        """Update an existing job and persist."""
        self._jobs[job.id] = job
        self.save()
        return job

    def remove(self, job_id: str) -> bool:
        """Remove a job by ID. Returns True if it existed."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            self.save()
            return True
        return False

    def all(self) -> list[CronJob]:
        """Return all jobs."""
        return list(self._jobs.values())

    def find_by_type(self, job_type: JobType) -> list[CronJob]:
        """Return all jobs of a given type."""
        return [j for j in self._jobs.values() if j.job_type == job_type]
