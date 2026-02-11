"""Agent-facing toolkit for managing tools at runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from agno.tools import Toolkit

from vandelay.tools.manager import ToolManager

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger("vandelay.tools.management")


class ToolManagementTools(Toolkit):
    """Lets the agent list, inspect, enable, and disable Agno tools at runtime."""

    def __init__(
        self,
        settings: Settings,
        reload_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(name="tool_management")
        self._settings = settings
        self._reload_callback = reload_callback or (lambda: None)
        self._manager = ToolManager()

        self.register(self.list_available_tools)
        self.register(self.get_tool_info)
        self.register(self.enable_tool)
        self.register(self.disable_tool)

    def list_available_tools(self) -> str:
        """List every available Agno tool grouped by category, showing which are enabled.

        Use this when the user asks what tools exist, what's available, or what can be installed.

        Returns:
            str: Formatted text listing all tools by category with enabled status.
        """
        enabled = set(self._settings.enabled_tools)
        by_cat = self._manager.registry.by_category()

        lines: list[str] = ["# Available Tools\n"]
        for category in sorted(by_cat):
            lines.append(f"## {category.title()}")
            for entry in sorted(by_cat[category], key=lambda e: e.name):
                mark = "[enabled]" if entry.name in enabled else ""
                desc = entry.description or "(no description)"
                # Truncate long descriptions for the listing
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                builtin_tag = "" if entry.is_builtin else " (requires install)"
                lines.append(f"- **{entry.name}** {mark}{builtin_tag}: {desc}")
            lines.append("")

        return "\n".join(lines)

    def get_tool_info(self, name: str) -> str:
        """Get detailed information about a specific tool.

        Args:
            name: The tool name (e.g. "shell", "calculator", "duckduckgo").

        Returns:
            str: Detailed info including description, methods, deps, and status.
        """
        entry = self._manager.registry.get(name)
        if entry is None:
            return f"Unknown tool: '{name}'. Use list_available_tools() to see all tools."

        enabled = name in self._settings.enabled_tools
        installed = self._manager._check_installed(entry)

        lines = [
            f"# Tool: {entry.name}",
            f"- **Class**: {entry.class_name}",
            f"- **Module**: {entry.module_path}",
            f"- **Category**: {entry.category}",
            f"- **Built-in**: {'yes' if entry.is_builtin else 'no'}",
            f"- **Enabled**: {'yes' if enabled else 'no'}",
            f"- **Installed**: {'yes' if installed else 'no'}",
        ]

        if entry.pip_dependencies:
            lines.append(f"- **Dependencies**: {', '.join(entry.pip_dependencies)}")

        if entry.description:
            lines.append(f"\n**Description**: {entry.description}")

        return "\n".join(lines)

    def enable_tool(self, name: str) -> str:
        """Enable a tool so it becomes active for the agent. Installs dependencies if needed.

        After enabling, the agent automatically reloads with the new tool available.

        Args:
            name: The tool name to enable (e.g. "calculator", "shell").

        Returns:
            str: Success or failure message.
        """
        entry = self._manager.registry.get(name)
        if entry is None:
            return f"Unknown tool: '{name}'. Use list_available_tools() to see all tools."

        if name in self._settings.enabled_tools:
            return f"Tool '{name}' is already enabled."

        # Install dependencies if needed
        if not entry.is_builtin:
            result = self._manager.install_deps(name)
            if not result.success:
                return f"Failed to install dependencies for '{name}': {result.message}"
            logger.info("Installed deps for tool '%s': %s", name, result.message)

        # Update settings
        self._settings.enabled_tools.append(name)
        self._settings.save()
        logger.info("Enabled tool '%s'", name)

        # Trigger hot reload
        self._reload_callback()

        return f"Tool '{name}' is now enabled and active. I've reloaded with the new tool."

    def disable_tool(self, name: str) -> str:
        """Disable a tool so it is no longer active for the agent.

        After disabling, the agent automatically reloads without the tool.

        Args:
            name: The tool name to disable (e.g. "calculator", "shell").

        Returns:
            str: Success or failure message.
        """
        if name not in self._settings.enabled_tools:
            return f"Tool '{name}' is not currently enabled."

        self._settings.enabled_tools.remove(name)
        self._settings.save()
        logger.info("Disabled tool '%s'", name)

        # Trigger hot reload
        self._reload_callback()

        return f"Tool '{name}' has been disabled. I've reloaded without it."
