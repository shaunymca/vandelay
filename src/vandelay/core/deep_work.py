"""Deep work session manager — autonomous background execution."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vandelay.channels.router import ChannelRouter
    from vandelay.config.settings import Settings

logger = logging.getLogger("vandelay.core.deep_work")


class SessionStatus(Enum):
    """Status of a deep work session."""

    pending = "pending"
    running = "running"
    completed = "completed"
    cancelled = "cancelled"
    timed_out = "timed_out"
    failed = "failed"


@dataclass
class DeepWorkSession:
    """Tracks the state of a single deep work session."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    objective: str = ""
    status: SessionStatus = SessionStatus.pending
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: str = ""
    error: str = ""
    channel: str = ""
    iterations_completed: int = 0
    max_iterations: int = 50
    max_time_minutes: int = 240

    @property
    def elapsed_minutes(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at or datetime.now(UTC)
        return (end - self.started_at).total_seconds() / 60.0

    @property
    def is_active(self) -> bool:
        return self.status in (SessionStatus.pending, SessionStatus.running)


class DeepWorkManager:
    """Manages autonomous deep work sessions.

    Creates a separate Team(mode="tasks") instance that runs as a background
    asyncio task. Progress updates are sent periodically to the user's channel.

    Only one active session at a time (v1).
    """

    def __init__(
        self,
        settings: Settings,
        channel_router: ChannelRouter | None = None,
    ) -> None:
        self._settings = settings
        self._channel_router = channel_router
        self._session: DeepWorkSession | None = None
        self._task: asyncio.Task | None = None
        self._cancel_event = asyncio.Event()

    @property
    def current_session(self) -> DeepWorkSession | None:
        return self._session

    async def start_session(
        self,
        objective: str,
        channel: str = "",
        max_iterations: int | None = None,
        max_time_minutes: int | None = None,
    ) -> str:
        """Launch a new deep work session.

        Returns a status message. Runs in background (default) or blocking
        based on config.
        """
        if self._session and self._session.is_active:
            return (
                f"A deep work session is already active (ID: {self._session.id}). "
                "Cancel it first with cancel_deep_work() before starting a new one."
            )

        cfg = self._settings.deep_work
        session = DeepWorkSession(
            objective=objective,
            channel=channel or cfg.progress_channel,
            max_iterations=max_iterations or cfg.max_iterations,
            max_time_minutes=max_time_minutes or cfg.max_time_minutes,
        )
        self._session = session
        self._cancel_event.clear()

        if cfg.background:
            self._task = asyncio.create_task(
                self._run_session(session), name=f"deep-work-{session.id}"
            )
            return (
                f"Deep work session started (ID: {session.id}).\n"
                f"Objective: {objective}\n"
                f"Limits: {session.max_iterations} iterations, "
                f"{session.max_time_minutes} min timeout.\n"
                f"Progress updates every {cfg.progress_interval_minutes} min. "
                "Use check_deep_work_status() to check progress, "
                "or cancel_deep_work() to stop."
            )
        else:
            await self._run_session(session)
            return self.get_status()

    def cancel_session(self) -> str:
        """Cancel the active deep work session."""
        if not self._session or not self._session.is_active:
            return "No active deep work session to cancel."

        self._cancel_event.set()
        if self._task and not self._task.done():
            self._task.cancel()

        self._session.status = SessionStatus.cancelled
        self._session.finished_at = datetime.now(UTC)
        return (
            f"Deep work session {self._session.id} cancelled after "
            f"{self._session.elapsed_minutes:.1f} minutes."
        )

    def get_status(self) -> str:
        """Return a formatted status string for the current/last session."""
        session = self._session
        if session is None:
            return "No deep work sessions have been run."

        lines = [
            f"# Deep Work Session: {session.id}",
            f"- **Status**: {session.status.value}",
            f"- **Objective**: {session.objective}",
            f"- **Elapsed**: {session.elapsed_minutes:.1f} minutes",
            f"- **Iterations**: {session.iterations_completed}/"
            f"{session.max_iterations}",
            f"- **Time limit**: {session.max_time_minutes} minutes",
        ]

        if session.result:
            # Truncate long results for status display
            result_preview = session.result[:500]
            if len(session.result) > 500:
                result_preview += "... (truncated)"
            lines.append(f"- **Result**: {result_preview}")

        if session.error:
            lines.append(f"- **Error**: {session.error}")

        return "\n".join(lines)

    async def _run_session(self, session: DeepWorkSession) -> None:
        """Execute the deep work session — build team, run, handle lifecycle."""
        session.status = SessionStatus.running
        session.started_at = datetime.now(UTC)

        progress_task: asyncio.Task | None = None
        timeout_seconds = session.max_time_minutes * 60

        try:
            team = self._build_deep_work_team(session)

            # Start progress reporter
            progress_task = asyncio.create_task(
                self._progress_loop(session), name=f"deep-work-progress-{session.id}"
            )

            # Run with timeout
            response = await asyncio.wait_for(
                team.arun(
                    session.objective,
                    user_id=self._settings.user_id or "default",
                    session_id=f"deep-work-{session.id}",
                ),
                timeout=timeout_seconds,
            )

            session.result = response.content if response and response.content else ""
            session.status = SessionStatus.completed

        except TimeoutError:
            session.status = SessionStatus.timed_out
            session.error = (
                f"Session timed out after {session.max_time_minutes} minutes."
            )
            logger.warning("Deep work session %s timed out", session.id)

        except asyncio.CancelledError:
            if self._cancel_event.is_set():
                session.status = SessionStatus.cancelled
            else:
                session.status = SessionStatus.failed
                session.error = "Session task was cancelled unexpectedly."
            logger.info("Deep work session %s cancelled", session.id)

        except Exception as exc:
            session.status = SessionStatus.failed
            session.error = str(exc)
            logger.error(
                "Deep work session %s failed: %s", session.id, exc, exc_info=True
            )

        finally:
            session.finished_at = datetime.now(UTC)
            if progress_task and not progress_task.done():
                progress_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await progress_task

        # Post-session actions
        if session.status == SessionStatus.completed:
            if self._settings.deep_work.save_results_to_workspace:
                self._save_to_workspace(session)
            await self._notify_completion(session)
        elif session.status in (SessionStatus.timed_out, SessionStatus.failed):
            await self._notify_completion(session)

    def _build_deep_work_team(self, session: DeepWorkSession) -> Any:
        """Create a Team(mode='tasks') for autonomous execution."""
        from agno.team import Team

        from vandelay.agents.factory import (
            _build_member_agent,
            _get_model,
            _resolve_member,
        )
        from vandelay.knowledge.setup import create_knowledge
        from vandelay.memory.setup import create_db

        settings = self._settings
        db = create_db(settings)
        model = _get_model(settings)
        knowledge = create_knowledge(settings, db=db)

        from vandelay.agents.prompts.system_prompt import build_personality_brief

        personality_brief = build_personality_brief(Path(settings.workspace_dir))

        # Build members from config
        members = []
        for entry in settings.team.members:
            mc = _resolve_member(entry)
            agent = _build_member_agent(
                mc,
                main_model=model,
                db=db,
                knowledge=knowledge,
                settings=settings,
                personality_brief=personality_brief,
            )
            members.append(agent)

        instructions = (
            f"You are running a deep work session. Your objective:\n\n"
            f"{session.objective}\n\n"
            "Break this into concrete tasks with dependencies. "
            "Delegate each task to the best team member. "
            "Evaluate results and iterate until the objective is fully met. "
            "When complete, provide a comprehensive summary of what was accomplished."
        )

        team = Team(
            id=f"vandelay-deep-work-{session.id}",
            name=f"{settings.agent_name} (Deep Work)",
            user_id=settings.user_id or "default",
            mode="tasks",
            members=members,
            model=model,
            db=db,
            knowledge=knowledge,
            search_knowledge=knowledge is not None,
            instructions=[instructions],
            markdown=True,
            max_iterations=session.max_iterations,
        )

        return team

    async def _progress_loop(self, session: DeepWorkSession) -> None:
        """Send periodic progress updates to the user's channel."""
        interval = self._settings.deep_work.progress_interval_minutes * 60
        try:
            while session.is_active:
                await asyncio.sleep(interval)
                if not session.is_active:
                    break
                await self._send_progress(session)
        except asyncio.CancelledError:
            pass

    async def _send_progress(self, session: DeepWorkSession) -> None:
        """Send a single progress update."""
        msg = (
            f"Deep work update ({session.elapsed_minutes:.0f}m elapsed): "
            f"Status: {session.status.value}, "
            f"Iterations: {session.iterations_completed}/{session.max_iterations}"
        )
        await self._send_to_channel(msg, session.channel)

    async def _notify_completion(self, session: DeepWorkSession) -> None:
        """Notify the user that the session has finished."""
        status = session.status.value
        elapsed = f"{session.elapsed_minutes:.1f}"

        if session.status == SessionStatus.completed:
            result_preview = session.result[:300] if session.result else "(no output)"
            if len(session.result) > 300:
                result_preview += "..."
            msg = (
                f"Deep work complete ({elapsed}m).\n\n"
                f"**Objective**: {session.objective}\n\n"
                f"**Result**: {result_preview}\n\n"
                "Use check_deep_work_status() for the full result."
            )
        else:
            msg = (
                f"Deep work session ended: {status} ({elapsed}m).\n"
                f"Objective: {session.objective}"
            )
            if session.error:
                msg += f"\nError: {session.error}"

        await self._send_to_channel(msg, session.channel)

    async def _send_to_channel(self, text: str, channel: str) -> None:
        """Send a message to the user via their channel."""
        if not self._channel_router:
            logger.info("Deep work notification (no channel): %s", text[:200])
            return

        from vandelay.channels.base import OutgoingMessage

        adapter = self._channel_router.get(channel) if channel else None
        if adapter is None:
            # Try first available channel
            channels = self._channel_router.active_channels
            if channels:
                adapter = self._channel_router.get(channels[0])

        if adapter is None:
            logger.info("Deep work notification (no adapter): %s", text[:200])
            return

        try:
            await adapter.send(OutgoingMessage(
                text=text,
                session_id=f"deep-work-{self._session.id if self._session else 'unknown'}",
                channel=channel,
            ))
        except Exception as exc:
            logger.warning("Failed to send deep work notification: %s", exc)

    def _save_to_workspace(self, session: DeepWorkSession) -> None:
        """Append session results to workspace MEMORY.md."""
        workspace_dir = Path(self._settings.workspace_dir)
        memory_path = workspace_dir / "MEMORY.md"

        entry = (
            f"\n\n## Deep Work: {session.objective[:80]}\n"
            f"*Completed {session.finished_at.strftime('%Y-%m-%d %H:%M UTC') if session.finished_at else 'unknown'}*\n"  # noqa: E501
            f"*Session {session.id} — {session.elapsed_minutes:.0f}m, "
            f"{session.iterations_completed} iterations*\n\n"
            f"{session.result}\n"
        )

        try:
            if memory_path.exists():
                existing = memory_path.read_text(encoding="utf-8")
                memory_path.write_text(existing + entry, encoding="utf-8")
            else:
                memory_path.write_text(f"# Memory\n{entry}", encoding="utf-8")
            logger.info("Deep work results saved to %s", memory_path)
        except OSError as exc:
            logger.warning("Failed to save deep work results: %s", exc)
