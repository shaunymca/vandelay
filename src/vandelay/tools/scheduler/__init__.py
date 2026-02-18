"""Agent-facing toolkit for managing scheduled jobs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.tools import Toolkit
from croniter import croniter

from vandelay.scheduler.models import CronJob

if TYPE_CHECKING:
    from vandelay.scheduler.engine import SchedulerEngine

logger = logging.getLogger("vandelay.tools.scheduler")


class SchedulerTools(Toolkit):
    """Lets the agent schedule, list, pause, resume, and delete cron jobs."""

    def __init__(self, engine: SchedulerEngine, default_timezone: str = "UTC") -> None:
        super().__init__(name="scheduler")
        self._engine = engine
        self._default_tz = default_timezone

        self.register(self.schedule_job)
        self.register(self.list_scheduled_jobs)
        self.register(self.get_job_details)
        self.register(self.pause_scheduled_job)
        self.register(self.resume_scheduled_job)
        self.register(self.delete_scheduled_job)

    def schedule_job(
        self,
        name: str,
        cron_expression: str,
        command: str,
        timezone: str | None = None,
    ) -> str:
        """Create a new recurring scheduled job.

        The job runs on the given cron schedule. Each time it fires,
        the command is sent to you (the agent) as a message and you
        execute it with your full tool access.

        Args:
            name: Human-readable name for the job (e.g. "Daily email check").
            cron_expression: Standard 5-field cron (e.g. "0 9 * * *" = every day at 9am).
            command: Natural language instruction to execute when the job fires.
            timezone: Timezone for the schedule. Defaults to the user's configured timezone.
                      Use IANA names like "America/New_York" or "Europe/London".

        Returns:
            str: Success message with job ID, or error description.
        """
        tz = timezone or self._default_tz
        if not croniter.is_valid(cron_expression):
            return (
                f"Invalid cron expression: '{cron_expression}'. "
                "Use standard 5-field format: minute hour day month weekday. "
                "Examples: '0 9 * * *' (daily 9am), '*/30 * * * *' (every 30min)."
            )

        job = CronJob(
            name=name,
            cron_expression=cron_expression,
            command=command,
            timezone=tz,
        )

        try:
            result = self._engine.add_job(job)
            return (
                f"Scheduled '{result.name}' (ID: {result.id}). "
                f"Cron: {result.cron_expression} ({result.timezone}). "
                f"Next run: {result.next_run.strftime('%Y-%m-%d %H:%M UTC') if result.next_run else 'pending'}."  # noqa: E501
            )
        except Exception as exc:
            return f"Failed to schedule job: {exc}"

    def list_scheduled_jobs(self) -> str:
        """List all scheduled jobs with their status.

        Returns:
            str: Formatted list of all jobs, or a message if none exist.
        """
        jobs = self._engine.list_jobs()
        if not jobs:
            return "No scheduled jobs."

        lines = ["# Scheduled Jobs\n"]
        for job in jobs:
            status = "enabled" if job.enabled else "paused"
            last = job.last_run.strftime("%Y-%m-%d %H:%M") if job.last_run else "never"
            nxt = job.next_run.strftime("%Y-%m-%d %H:%M") if job.next_run else "N/A"
            lines.append(
                f"- **{job.name}** (ID: {job.id}) [{status}]\n"
                f"  Cron: `{job.cron_expression}` | Type: {job.job_type.value} | "
                f"Runs: {job.run_count} | Last: {last} | Next: {nxt}"
            )

        return "\n".join(lines)

    def get_job_details(self, job_id: str) -> str:
        """Get detailed information about a specific scheduled job.

        Args:
            job_id: The job ID to look up.

        Returns:
            str: Detailed job info, or error if not found.
        """
        job = self._engine.get_job(job_id)
        if job is None:
            return f"Job '{job_id}' not found."

        lines = [
            f"# Job: {job.name}",
            f"- **ID**: {job.id}",
            f"- **Cron**: {job.cron_expression}",
            f"- **Command**: {job.command}",
            f"- **Type**: {job.job_type.value}",
            f"- **Status**: {'enabled' if job.enabled else 'paused'}",
            f"- **Timezone**: {job.timezone}",
            f"- **Created**: {job.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"- **Last run**: {job.last_run.strftime('%Y-%m-%d %H:%M') if job.last_run else 'never'}",  # noqa: E501
            f"- **Next run**: {job.next_run.strftime('%Y-%m-%d %H:%M') if job.next_run else 'N/A'}",
            f"- **Run count**: {job.run_count}",
        ]
        if job.last_result:
            lines.append(f"- **Last result**: {job.last_result[:200]}")

        return "\n".join(lines)

    def pause_scheduled_job(self, job_id: str) -> str:
        """Pause a scheduled job without deleting it.

        Args:
            job_id: The job ID to pause.

        Returns:
            str: Success or error message.
        """
        job = self._engine.pause_job(job_id)
        if job is None:
            return f"Job '{job_id}' not found."
        return f"Paused '{job.name}' (ID: {job.id}). Use resume to re-enable."

    def resume_scheduled_job(self, job_id: str) -> str:
        """Resume a paused scheduled job.

        Args:
            job_id: The job ID to resume.

        Returns:
            str: Success or error message.
        """
        job = self._engine.resume_job(job_id)
        if job is None:
            return f"Job '{job_id}' not found."
        return (
            f"Resumed '{job.name}' (ID: {job.id}). "
            f"Next run: {job.next_run.strftime('%Y-%m-%d %H:%M UTC') if job.next_run else 'pending'}."  # noqa: E501
        )

    def delete_scheduled_job(self, job_id: str) -> str:
        """Permanently delete a scheduled job.

        Args:
            job_id: The job ID to delete.

        Returns:
            str: Success or error message.
        """
        removed = self._engine.remove_job(job_id)
        if removed:
            return f"Deleted job '{job_id}'."
        return f"Job '{job_id}' not found."
