"""Tool manager — enables/disables tools and instantiates them for the agent."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

from vandelay.tools.registry import ToolEntry, ToolRegistry

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


class InstallResult:
    """Result of a tool install/uninstall operation."""

    def __init__(self, success: bool, message: str, tool_name: str) -> None:
        self.success = success
        self.message = message
        self.tool_name = tool_name


class ToolManager:
    """High-level tool operations: enable, disable, install, instantiate."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or ToolRegistry()

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def list_tools(
        self,
        enabled_tools: list[str] | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all tools with their status. Returns dicts for easy display."""
        enabled = set(enabled_tools or [])
        result = []

        for name, entry in sorted(self._registry.tools.items()):
            if category and entry.category != category:
                continue

            installed = self._check_installed(entry)
            result.append({
                "name": name,
                "class_name": entry.class_name,
                "category": entry.category,
                "is_builtin": entry.is_builtin,
                "pip_dependencies": entry.pip_dependencies,
                "enabled": name in enabled,
                "installed": installed,
            })

        return result

    def _check_installed(self, entry: ToolEntry) -> bool:
        """Check if a tool's dependencies are importable."""
        if entry.is_builtin:
            return True
        try:
            __import__(entry.module_path)
            return True
        except ImportError:
            return False

    def install_deps(self, tool_name: str) -> InstallResult:
        """Install a tool's pip dependencies using uv."""
        entry = self._registry.get(tool_name)
        if entry is None:
            return InstallResult(False, f"Unknown tool: {tool_name}", tool_name)

        if entry.is_builtin:
            return InstallResult(True, "Built-in tool, no deps needed.", tool_name)

        deps = entry.pip_dependencies
        if not deps:
            return InstallResult(True, "No dependencies to install.", tool_name)

        try:
            result = subprocess.run(
                ["uv", "add", *deps],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return InstallResult(True, f"Installed: {', '.join(deps)}", tool_name)
            else:
                return InstallResult(
                    False,
                    f"uv add failed:\n{result.stderr.strip()}",
                    tool_name,
                )
        except FileNotFoundError:
            return InstallResult(
                False,
                "uv not found. Install it: https://docs.astral.sh/uv/",
                tool_name,
            )
        except subprocess.TimeoutExpired:
            return InstallResult(False, "Install timed out after 120s.", tool_name)

    def uninstall_deps(self, tool_name: str) -> InstallResult:
        """Remove a tool's pip dependencies using uv."""
        entry = self._registry.get(tool_name)
        if entry is None:
            return InstallResult(False, f"Unknown tool: {tool_name}", tool_name)

        if entry.is_builtin:
            return InstallResult(True, "Built-in tool, nothing to remove.", tool_name)

        deps = entry.pip_dependencies
        if not deps:
            return InstallResult(True, "No dependencies to remove.", tool_name)

        try:
            result = subprocess.run(
                ["uv", "remove", *deps],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return InstallResult(True, f"Removed: {', '.join(deps)}", tool_name)
            else:
                return InstallResult(
                    False,
                    f"uv remove failed:\n{result.stderr.strip()}",
                    tool_name,
                )
        except FileNotFoundError:
            return InstallResult(False, "uv not found.", tool_name)
        except subprocess.TimeoutExpired:
            return InstallResult(False, "Uninstall timed out after 120s.", tool_name)

    def instantiate_tools(self, enabled_tools: list[str], settings: Settings | None = None) -> list:
        """Create Toolkit instances for all enabled tools. Returns list of Agno Toolkit objects."""
        import importlib
        import io
        import logging
        import sys

        logger = logging.getLogger("vandelay.tools")
        instances = []

        for tool_name in enabled_tools:
            entry = self._registry.get(tool_name)
            if entry is None:
                continue

            try:
                # Special handling for shell — wrap with safety guard
                if tool_name == "shell" and settings is not None:
                    from vandelay.tools.safety import create_safe_shell_tools
                    instance = create_safe_shell_tools(settings)
                    instances.append(instance)
                    continue

                # Special handling for camofox — pass base_url
                if tool_name == "camofox":
                    from vandelay.tools.camofox import CamofoxTools
                    instances.append(CamofoxTools())
                    continue

                # Special handling for Google OAuth tools — shared token
                _goauth = {
                    "gmail": ("token_path", "port"),
                    "google_drive": ("token_path", "auth_port"),
                    "googlecalendar": ("token_path", "oauth_port"),
                    "googlesheets": ("token_path", "oauth_port"),
                }
                if tool_name in _goauth:
                    from vandelay.config.constants import VANDELAY_HOME
                    mod = importlib.import_module(entry.module_path)
                    cls = getattr(mod, entry.class_name)
                    tk, pk = _goauth[tool_name]
                    token = str(VANDELAY_HOME / "google_token.json")
                    instances.append(cls(**{tk: token, pk: 0}))
                    continue

                mod = importlib.import_module(entry.module_path)
                cls = getattr(mod, entry.class_name)

                # Suppress noisy stdout/stderr from Agno toolkit constructors
                # (e.g. "newspaper4k not installed" prints before raising)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                try:
                    instances.append(cls())
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr
            except Exception as e:
                # Skip tools that can't be loaded (missing deps, missing API keys, etc.)
                logger.debug("Skipping tool %s: %s", tool_name, e)

        return instances

    def refresh(self) -> int:
        """Refresh the tool registry from the installed agno package."""
        return self._registry.refresh()

    def categories(self) -> list[str]:
        """List all available categories."""
        return sorted(set(t.category for t in self._registry.tools.values()))
