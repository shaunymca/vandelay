"""Agent-facing toolkit for managing deep work sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.tools import Toolkit

if TYPE_CHECKING:
    from vandelay.core.deep_work import DeepWorkManager

logger = logging.getLogger("vandelay.tools.deep_work")


class DeepWorkTools(Toolkit):
    """Lets the agent start, monitor, and cancel deep work sessions."""

    def __init__(self, manager: DeepWorkManager) -> None:
        super().__init__(name="deep_work")
        self._manager = manager

        self.register(self.start_deep_work)
        self.register(self.check_deep_work_status)
        self.register(self.cancel_deep_work)

    async def start_deep_work(
        self,
        objective: str,
        max_iterations: int | None = None,
        max_time_minutes: int | None = None,
    ) -> str:
        """Start an autonomous deep work session for a complex, multi-step task.

        Deep work runs in the background as a separate team that decomposes the
        objective into tasks, delegates to specialists, evaluates results, and
        iterates until the objective is met. Progress updates are sent periodically.

        Use this for tasks that require extended research, multi-step implementation,
        or any work that would take significant time and multiple tool calls.

        Args:
            objective: Clear description of what needs to be accomplished.
                Be specific about the desired outcome and any constraints.
            max_iterations: Maximum number of task iterations (default: from config).
            max_time_minutes: Maximum time in minutes (default: from config).

        Returns:
            str: Session launch confirmation with ID and limits, or error if
                a session is already active.
        """
        return await self._manager.start_session(
            objective=objective,
            max_iterations=max_iterations,
            max_time_minutes=max_time_minutes,
        )

    def check_deep_work_status(self) -> str:
        """Check the status of the current or most recent deep work session.

        Returns:
            str: Formatted status including objective, elapsed time, iteration
                count, and result preview (if completed).
        """
        return self._manager.get_status()

    def cancel_deep_work(self) -> str:
        """Cancel the currently running deep work session.

        The session will be stopped gracefully and marked as cancelled.
        Any partial results will be preserved.

        Returns:
            str: Cancellation confirmation with elapsed time, or message
                if no active session exists.
        """
        return self._manager.cancel_session()
