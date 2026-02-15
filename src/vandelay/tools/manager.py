"""Tool manager — enables/disables tools and instantiates them for the agent."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vandelay.tools.registry import ToolEntry, ToolRegistry


def _find_project_root() -> str | None:
    """Walk up from this file's location to find the directory containing pyproject.toml."""
    current = Path(__file__).resolve().parent
    for parent in (current, *current.parents):
        if (parent / "pyproject.toml").exists():
            return str(parent)
    return None

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


def _google_all_scopes() -> list[str]:
    """All OAuth scopes needed across Google tools."""
    return [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]


def _inject_google_creds(tool_instance: Any, token_path: str) -> None:
    """Pre-load Google credentials and inject into a tool instance.

    This prevents Agno's per-tool ``_auth()`` from overwriting
    Vandelay's unified multi-scope token or attempting to open a
    browser for OAuth on a headless server.
    """
    import logging
    from pathlib import Path
    from types import MethodType

    logger = logging.getLogger("vandelay.tools")
    token_file = Path(token_path)
    all_scopes = _google_all_scopes()

    if token_file.exists():
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(str(token_file), all_scopes)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_file.write_text(creds.to_json())
            if creds and creds.valid:
                tool_instance.creds = creds
        except Exception as e:
            logger.warning("Failed to pre-load Google creds: %s", e)

    # Replace _auth() with a safe version that only refreshes — never
    # opens a browser or overwrites the token with single-scope creds.
    def _safe_auth(self: Any) -> None:
        if self.creds and self.creds.valid:
            return
        _token = Path(token_path)
        if not _token.exists():
            logger.error(
                "Google token missing. Run: vandelay tools auth-google"
            )
            return
        try:
            from google.auth.transport.requests import Request as _Req
            from google.oauth2.credentials import Credentials as _Creds

            self.creds = _Creds.from_authorized_user_file(
                str(_token), all_scopes
            )
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(_Req())
                _token.write_text(self.creds.to_json())
            if not self.creds or not self.creds.valid:
                logger.error(
                    "Google token expired. Run: vandelay tools auth-google --reauth"
                )
        except Exception as exc:
            logger.error("Google auth refresh failed: %s", exc)

    tool_instance._auth = MethodType(_safe_auth, tool_instance)


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
                cwd=_find_project_root(),
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
                cwd=_find_project_root(),
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

                # Special handling for file — sandbox to user home
                if tool_name == "file":
                    from pathlib import Path
                    home_dir = Path.home()
                    mod = importlib.import_module(entry.module_path)
                    cls = getattr(mod, entry.class_name)
                    instances.append(cls(base_dir=home_dir))
                    continue

                # Special handling for camofox — pass base_url
                if tool_name == "camofox":
                    from vandelay.tools.camofox import CamofoxTools
                    instances.append(CamofoxTools())
                    continue

                # Special handling for Google OAuth tools — shared token
                # and unified credential management.
                #
                # Problem: Each Agno Google tool has its own _auth() that can
                # (a) load the token with wrong/tool-specific scopes,
                # (b) overwrite the token file with single-scope credentials,
                # (c) try to open a browser for OAuth on a headless server.
                #
                # Fix: Pre-load credentials from Vandelay's unified token
                # (all 4 scopes) and inject into the tool instance. Replace
                # _auth() with a safe version that only refreshes — never
                # re-runs OAuth.
                _goauth = {
                    "gmail": {"token_path": None, "port": 0},
                    "google_drive": {"token_path": None, "auth_port": 0},
                    "googlecalendar": {"token_path": None, "oauth_port": 0},
                    "googlesheets": {"token_path": None, "oauth_port": 0},
                }
                if tool_name in _goauth:
                    from vandelay.config.constants import VANDELAY_HOME
                    mod = importlib.import_module(entry.module_path)
                    cls = getattr(mod, entry.class_name)
                    kwargs = dict(_goauth[tool_name])
                    token = str(VANDELAY_HOME / "google_token.json")
                    # Set token_path (key name varies per tool)
                    for k in kwargs:
                        if "token" in k:
                            kwargs[k] = token
                            break
                    # Pass all scopes to every Google tool so scope
                    # validation works and refreshes keep all scopes.
                    kwargs["scopes"] = _google_all_scopes()
                    if tool_name == "googlecalendar":
                        from vandelay.config.settings import get_settings
                        _settings = get_settings()
                        kwargs["calendar_id"] = _settings.google.calendar_id
                        kwargs["allow_update"] = True
                    instance = cls(**kwargs)
                    _inject_google_creds(instance, token)
                    instances.append(instance)
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
