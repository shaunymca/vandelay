"""Scheduler engine — APScheduler bridge that sends cron jobs through ChatService."""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from vandelay.channels.base import IncomingMessage
from vandelay.scheduler.models import CronJob, JobType
from vandelay.scheduler.store import CronJobStore

if TYPE_CHECKING:
    from vandelay.config.settings import Settings
    from vandelay.core.chat_service import ChatService

logger = logging.getLogger("vandelay.scheduler.engine")

HEARTBEAT_JOB_ID = "__heartbeat__"
HEARTBEAT_COMMAND = (
    "Run your HEARTBEAT.md checklist now. "
    "Respond with HEARTBEAT_OK if everything is fine, "
    "or alert the user on their primary channel if something needs attention."
)


class SchedulerEngine:
    """Manages cron jobs via APScheduler, routing triggers through ChatService.

    Each job fires a natural-language command into the agent via ChatService.run().
    The agent handles execution with full tool access.
    """

    def __init__(
        self,
        settings: Settings,
        chat_service: ChatService,
        store: CronJobStore | None = None,
    ) -> None:
        self._settings = settings
        self._chat_service = chat_service
        self._store = store or CronJobStore()
        self._scheduler = AsyncIOScheduler()

    # -- Lifecycle -------------------------------------------------------------

    async def start(self) -> None:
        """Load all enabled jobs into APScheduler and start the scheduler."""
        self._sync_heartbeat_job()

        for job in self._store.all():
            if job.enabled:
                self._register_job(job)

        self._scheduler.start()
        count = len(self._store.all())
        logger.info("Scheduler started with %d jobs", count)

    async def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    # -- Job management --------------------------------------------------------

    def add_job(self, job: CronJob) -> CronJob:
        """Validate, persist, and register a new job."""
        if not croniter.is_valid(job.cron_expression):
            raise ValueError(f"Invalid cron expression: {job.cron_expression}")

        # Compute next_run
        cron = croniter(job.cron_expression)
        job.next_run = cron.get_next(datetime).replace(tzinfo=UTC)

        self._store.add(job)
        if job.enabled and self._scheduler.running:
            self._register_job(job)

        logger.info("Added job %s (%s): %s", job.id, job.name, job.cron_expression)
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the scheduler and store."""
        self._unregister_job(job_id)
        removed = self._store.remove(job_id)
        if removed:
            logger.info("Removed job %s", job_id)
        return removed

    def pause_job(self, job_id: str) -> CronJob | None:
        """Pause a job (disable without deleting)."""
        job = self._store.get(job_id)
        if job is None:
            return None
        job.enabled = False
        self._store.update(job)
        self._unregister_job(job_id)
        logger.info("Paused job %s (%s)", job_id, job.name)
        return job

    def resume_job(self, job_id: str) -> CronJob | None:
        """Resume a paused job."""
        job = self._store.get(job_id)
        if job is None:
            return None
        job.enabled = True

        # Recompute next_run
        cron = croniter(job.cron_expression)
        job.next_run = cron.get_next(datetime).replace(tzinfo=UTC)

        self._store.update(job)
        if self._scheduler.running:
            self._register_job(job)
        logger.info("Resumed job %s (%s)", job_id, job.name)
        return job

    def list_jobs(self) -> list[CronJob]:
        """Return all jobs."""
        return self._store.all()

    def get_job(self, job_id: str) -> CronJob | None:
        """Retrieve a single job by ID."""
        return self._store.get(job_id)

    # -- Execution callback ----------------------------------------------------

    async def _execute_job(self, job_id: str) -> None:
        """Called by APScheduler when a job fires."""
        job = self._store.get(job_id)
        if job is None:
            logger.warning("Triggered job %s not found in store", job_id)
            return

        logger.info("Executing job %s (%s): %s", job_id, job.name, job.command)

        message = IncomingMessage(
            text=job.command,
            session_id=f"scheduler-{job.id}",
            user_id="scheduler",
            channel="scheduler",
        )

        result = await self._chat_service.run(message)

        # Update job metadata
        job.last_run = datetime.now(UTC)
        job.run_count += 1
        job.last_result = result.content[:500] if result.content else result.error

        # Recompute next_run
        cron = croniter(job.cron_expression)
        job.next_run = cron.get_next(datetime).replace(tzinfo=UTC)

        self._store.update(job)

        # Heartbeat logging
        if job.job_type == JobType.HEARTBEAT:
            if result.content and "HEARTBEAT_OK" in result.content:
                logger.debug("Heartbeat OK")
            else:
                logger.warning(
                    "Heartbeat response (agent may have sent an alert): %s",
                    (result.content or result.error or "")[:200],
                )

    # -- Internal helpers ------------------------------------------------------

    def _register_job(self, job: CronJob) -> None:
        """Add a job to APScheduler (replacing if it already exists)."""
        try:
            parts = job.cron_expression.split()
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone=job.timezone,
            )
            self._scheduler.add_job(
                self._execute_job,
                trigger=trigger,
                args=[job.id],
                id=job.id,
                replace_existing=True,
                name=job.name,
            )
        except Exception:
            logger.exception("Failed to register job %s in APScheduler", job.id)

    def _unregister_job(self, job_id: str) -> None:
        """Remove a job from APScheduler if it exists."""
        with contextlib.suppress(Exception):
            self._scheduler.remove_job(job_id)

    def _sync_heartbeat_job(self) -> None:
        """Create or update the heartbeat job from HeartbeatConfig."""
        hb = self._settings.heartbeat

        if not hb.enabled:
            # Remove heartbeat job if it exists
            existing = self._store.get(HEARTBEAT_JOB_ID)
            if existing:
                self._store.remove(HEARTBEAT_JOB_ID)
                logger.debug("Heartbeat disabled, removed heartbeat job")
            return

        # Build cron expression: */interval active_start-active_end * * *
        interval = hb.interval_minutes
        start_h = hb.active_hours_start
        end_h = hb.active_hours_end
        cron_expr = f"*/{interval} {start_h}-{end_h} * * *"

        tz = hb.timezone or self._settings.timezone

        existing = self._store.get(HEARTBEAT_JOB_ID)
        if existing:
            # Update if config changed
            existing.cron_expression = cron_expr
            existing.timezone = tz
            existing.enabled = True
            existing.command = HEARTBEAT_COMMAND
            self._store.update(existing)
            logger.debug("Updated heartbeat job: %s (tz=%s)", cron_expr, tz)
        else:
            job = CronJob(
                id=HEARTBEAT_JOB_ID,
                name="Heartbeat",
                cron_expression=cron_expr,
                command=HEARTBEAT_COMMAND,
                job_type=JobType.HEARTBEAT,
                timezone=tz,
            )
            self._store.add(job)
            logger.info("Created heartbeat job: %s (tz=%s)", cron_expr, tz)
