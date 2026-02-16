"""Agent-facing toolkit for managing team members at runtime."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from agno.tools import Toolkit

from vandelay.config.constants import MEMBERS_DIR
from vandelay.config.models import MemberConfig

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger("vandelay.tools.member_management")

_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


class MemberManagementTools(Toolkit):
    """Lets the leader list, add, update, and remove team members at runtime."""

    def __init__(
        self,
        settings: Settings,
        reload_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(name="member_management")
        self._settings = settings
        self._reload_callback = reload_callback or (lambda: None)

        self.register(self.list_team_members)
        self.register(self.add_team_member)
        self.register(self.update_member_config)
        self.register(self.update_member_instructions)
        self.register(self.remove_team_member)

    def _resolve(self, m: str | MemberConfig) -> MemberConfig:
        """Normalize a member entry to MemberConfig."""
        if isinstance(m, MemberConfig):
            return m
        from vandelay.agents.factory import _resolve_member
        return _resolve_member(m)

    def _find_member(self, name: str) -> tuple[int, MemberConfig] | None:
        """Find a member by name, returning (index, config) or None."""
        for i, m in enumerate(self._settings.team.members):
            n = m if isinstance(m, str) else m.name
            if n == name:
                mc = self._resolve(m)
                self._settings.team.members[i] = mc
                return i, mc
        return None

    def _member_names(self) -> list[str]:
        return [m if isinstance(m, str) else m.name for m in self._settings.team.members]

    def list_team_members(self) -> str:
        """List all current team members with their roles, tools, and model overrides.

        Returns:
            str: Formatted list of team members.
        """
        members = self._settings.team.members
        if not members:
            return "No team members configured. Use add_team_member() to add one."

        lines = ["# Team Members\n"]
        for m in members:
            mc = self._resolve(m)
            tools = ", ".join(mc.tools) if mc.tools else "(none)"
            model = f"{mc.model_provider}:{mc.model_id}" if mc.model_provider else "(inherit)"
            instr = mc.instructions_file or "(none)"
            lines.append(f"- **{mc.name}**: {mc.role or '(no role)'}")
            lines.append(f"  - Tools: {tools}")
            lines.append(f"  - Model: {model}")
            lines.append(f"  - Instructions file: {instr}")
        return "\n".join(lines)

    def add_team_member(
        self, name: str, role: str, tools: str = "", instructions: str = ""
    ) -> str:
        """Add a new team member to the team.

        After adding, the team automatically reloads with the new member available.

        Args:
            name: Member name (alphanumeric + underscores, must start with letter).
            role: Short description of the member's role (e.g. "DevOps specialist").
            tools: Comma-separated tool names to assign (e.g. "shell,docker").
            instructions: Optional markdown instructions for the member's system prompt.

        Returns:
            str: Success or error message.
        """
        name = name.strip()
        if not _NAME_RE.match(name):
            return (
                f"Invalid name '{name}'. "
                "Must start with a letter and contain only letters, numbers, and underscores."
            )

        existing = self._member_names()
        if name in existing:
            return f"A member named '{name}' already exists. Use update_member_config() instead."

        # Parse and validate tools
        tool_list = [t.strip() for t in tools.split(",") if t.strip()] if tools else []
        enabled = set(self._settings.enabled_tools)
        unenabled = [t for t in tool_list if t not in enabled]
        warnings = ""
        if unenabled:
            warnings = (
                f" Warning: these tools are not globally enabled and won't be "
                f"available until enabled: {', '.join(unenabled)}."
            )

        # Write instructions file if provided
        instructions_file = ""
        if instructions.strip():
            MEMBERS_DIR.mkdir(parents=True, exist_ok=True)
            path = MEMBERS_DIR / f"{name}.md"
            path.write_text(instructions.strip() + "\n", encoding="utf-8")
            instructions_file = f"{name}.md"

        mc = MemberConfig(
            name=name,
            role=role,
            tools=tool_list,
            instructions_file=instructions_file,
        )
        self._settings.team.members.append(mc)
        self._settings.save()
        self._reload_callback()

        logger.info("Added team member '%s' with role '%s'", name, role)
        return f"Member '{name}' added with role '{role}' and tools [{', '.join(tool_list)}].{warnings}"

    def update_member_config(self, name: str, role: str = "", tools: str = "") -> str:
        """Update a team member's role or tool list.

        Pass an empty string for role or tools to leave them unchanged.
        After updating, the team automatically reloads.

        Args:
            name: The member name to update.
            role: New role description (empty = keep current).
            tools: Comma-separated tool names to replace current list (empty = keep current).

        Returns:
            str: Success or error message.
        """
        result = self._find_member(name)
        if result is None:
            return f"Unknown member '{name}'. Available: {', '.join(self._member_names())}"

        _, mc = result
        changes = []

        if role:
            mc.role = role
            changes.append(f"role → '{role}'")

        if tools:
            tool_list = [t.strip() for t in tools.split(",") if t.strip()]
            mc.tools = tool_list
            changes.append(f"tools → [{', '.join(tool_list)}]")

        if not changes:
            return "Nothing to update — pass role or tools to change."

        self._settings.save()
        self._reload_callback()

        logger.info("Updated member '%s': %s", name, ", ".join(changes))
        return f"Member '{name}' updated: {', '.join(changes)}. Team reloaded."

    def update_member_instructions(self, name: str, instructions: str) -> str:
        """Write or replace the markdown instructions for a team member.

        Instructions are saved to ~/.vandelay/members/<name>.md and loaded into the
        member's system prompt at runtime. After updating, the team reloads.

        Args:
            name: The member name to update.
            instructions: Markdown content for the member's system prompt.

        Returns:
            str: Success or error message.
        """
        if not instructions.strip():
            return "Instructions cannot be empty."

        result = self._find_member(name)
        if result is None:
            return f"Unknown member '{name}'. Available: {', '.join(self._member_names())}"

        _, mc = result

        MEMBERS_DIR.mkdir(parents=True, exist_ok=True)
        path = MEMBERS_DIR / f"{name}.md"
        path.write_text(instructions.strip() + "\n", encoding="utf-8")
        mc.instructions_file = f"{name}.md"

        self._settings.save()
        self._reload_callback()

        logger.info("Updated instructions for member '%s'", name)
        return f"Instructions for '{name}' saved to {path}. Team reloaded."

    def remove_team_member(self, name: str) -> str:
        """Remove a team member from the team.

        The member's instruction file (if any) is kept for reuse.
        After removing, the team automatically reloads.

        Args:
            name: The member name to remove.

        Returns:
            str: Success or error message.
        """
        members = self._settings.team.members
        idx = None
        for i, m in enumerate(members):
            n = m if isinstance(m, str) else m.name
            if n == name:
                idx = i
                break

        if idx is None:
            return f"Unknown member '{name}'. Available: {', '.join(self._member_names())}"

        members.pop(idx)
        self._settings.save()
        self._reload_callback()

        logger.info("Removed team member '%s'", name)
        return (
            f"Member '{name}' removed from the team. "
            f"Instruction file (if any) preserved for reuse. Team reloaded."
        )
