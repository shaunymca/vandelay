"""Lightweight toolkit for team members to request tools they don't have."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.tools import Toolkit

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)


class ToolRequestTools(Toolkit):
    """Lets team members request tools from the leader."""

    def __init__(self, settings: Settings, member_name: str) -> None:
        super().__init__(name="tool_request")
        self._settings = settings
        self._member_name = member_name

        self.register(self.request_tool)

    def request_tool(self, tool_name: str, reason: str) -> str:
        """Request a tool you don't currently have from the team leader.

        Use this when a task requires a tool that isn't in your available tools.
        The leader will either assign it to you, enable it, or explain why it's
        not available.

        Args:
            tool_name: The tool you need (e.g. "notion", "gmail", "github").
            reason: Why you need this tool — what task requires it (1-2 sentences).

        Returns:
            str: A structured message for the leader to act on.
        """
        from vandelay.tools.registry import ToolRegistry

        registry = ToolRegistry()
        entry = registry.get(tool_name)

        # Check if this member already has the tool assigned
        for m in self._settings.team.members:
            name = m if isinstance(m, str) else m.name
            if name == self._member_name:
                member_tools = [] if isinstance(m, str) else list(m.tools)
                if tool_name in member_tools and tool_name in self._settings.enabled_tools:
                    return (
                        f"'{tool_name}' is already in your toolkit — use its functions directly. "
                        f"Do not request it again."
                    )
                break

        if entry is None:
            status = "not_found"
        elif tool_name in self._settings.enabled_tools:
            status = "enabled_not_assigned"
        else:
            status = "not_enabled"

        logger.info(
            "Member %s requesting tool %s (status=%s): %s",
            self._member_name, tool_name, status, reason,
        )

        return (
            f"TOOL_REQUEST: tool={tool_name}, status={status}, "
            f"reason={reason}, requesting_member={self._member_name}"
        )
