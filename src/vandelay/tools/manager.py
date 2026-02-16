"""Tool manager — enables/disables tools and instantiates them for the agent."""

from __future__ import annotations

import subprocess
from functools import wraps
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


def _guard_file_writes(tool_instance: Any) -> None:
    """Wrap FileTools write methods to only allow writes to safe directories.

    Allowed write targets:
      - ~/work/          — agent scratchpad for scripts and output
      - ~/.vandelay/workspace/  — workspace templates and memory
      - ~/.vandelay/.env        — API key management
      - ~/.vandelay/cron_jobs.json  — cron config
      - ~/.vandelay/task_queue.json — task queue

    Everything else under home is read-only.
    """
    from pathlib import Path

    from vandelay.config.constants import VANDELAY_HOME

    home = Path.home()
    _WRITE_ALLOWED = [
        home / "work",
        VANDELAY_HOME / "workspace",
        VANDELAY_HOME / "custom_tools",
        VANDELAY_HOME / "members",
        VANDELAY_HOME / ".env",
        VANDELAY_HOME / "cron_jobs.json",
        VANDELAY_HOME / "task_queue.json",
    ]

    def _is_allowed(path_str: str) -> bool:
        try:
            p = Path(path_str).resolve()
        except (OSError, ValueError):
            return False
        for allowed in _WRITE_ALLOWED:
            allowed_r = allowed.resolve()
            # Exact file match or path is inside allowed directory
            if p == allowed_r or allowed_r in p.parents:
                return True
        return False

    for method_name in ("save_file", "replace_file_chunk", "delete_file"):
        original = getattr(tool_instance, method_name, None)
        if original is None:
            continue

        @wraps(original)
        def guarded(*, _orig=original, _mname=method_name, **kwargs):
            file_name = kwargs.get("file_name", "")
            if not _is_allowed(file_name):
                return (
                    f"BLOCKED: Cannot write to '{file_name}'. "
                    "Writes are only allowed in ~/work/ and ~/.vandelay/workspace/. "
                    "Ask the user if you need to write elsewhere."
                )
            return _orig(**kwargs)

        setattr(tool_instance, method_name, guarded)


def _fix_gmail_html_body(tool_instance: Any) -> None:
    """Wrap Gmail _get_message_body to fall back to HTML when plain text is empty.

    Forwarded emails (especially from Outlook/Exchange) store the thread
    only in text/html — the text/plain part is empty. Agno's implementation
    only reads text/plain, so forwarded threads appear blank.
    """
    import base64
    import re

    original = tool_instance._get_message_body

    @wraps(original)
    def patched_get_message_body(msg_data: dict) -> str:
        result = original(msg_data)

        # Strip the "Attachments:" suffix to check if the actual body is empty
        body_text = re.sub(r"\n\nAttachments:.*$", "", result).strip()
        if body_text:
            return result

        # Plain text was empty — try extracting from text/html parts
        try:
            html_body = ""
            payload = msg_data.get("payload", {})
            parts = payload.get("parts", [])

            # Check top-level parts
            for part in parts:
                if part.get("mimeType") == "text/html" and "data" in part.get("body", {}):
                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                    break
                # Check nested multipart/alternative
                for sub in part.get("parts", []):
                    if sub.get("mimeType") == "text/html" and "data" in sub.get("body", {}):
                        html_body = base64.urlsafe_b64decode(sub["body"]["data"]).decode()
                        break
                if html_body:
                    break

            if not html_body:
                return result

            # Strip HTML tags to get readable text
            text = re.sub(r"<style[^>]*>.*?</style>", "", html_body, flags=re.DOTALL)
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", "", text)
            # Clean up whitespace
            text = re.sub(r"&nbsp;", " ", text)
            text = re.sub(r"&amp;", "&", text)
            text = re.sub(r"&lt;", "<", text)
            text = re.sub(r"&gt;", ">", text)
            text = re.sub(r"&#\d+;", "", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()

            # Re-append attachments if the original had them
            attachments_match = re.search(r"\n\nAttachments:.*$", result)
            if attachments_match:
                text += attachments_match.group()

            return text if text else result
        except Exception:
            return result

    tool_instance._get_message_body = patched_get_message_body


def _cap_sheet_output(tool_instance: Any, max_chars: int = 50_000) -> None:
    """Wrap read_sheet to truncate large results and prevent token overflow."""
    original = tool_instance.read_sheet

    @wraps(original)
    def capped_read_sheet(*args, **kwargs):
        result = original(*args, **kwargs)
        if isinstance(result, str) and len(result) > max_chars:
            return (
                result[:max_chars]
                + f"\n\n[TRUNCATED — output was {len(result):,} chars, limit is {max_chars:,}. "
                "Use a narrower spreadsheet_range (e.g. 'Sheet1!A1:F50') to read smaller sections.]"
            )
        return result

    tool_instance.read_sheet = capped_read_sheet


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
                "pricing": entry.pricing,
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
                # and block writes to source code
                if tool_name == "file":
                    from pathlib import Path
                    home_dir = Path.home()
                    mod = importlib.import_module(entry.module_path)
                    cls = getattr(mod, entry.class_name)
                    instance = cls(base_dir=home_dir)
                    _guard_file_writes(instance)
                    instances.append(instance)
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
                    if tool_name == "googlesheets":
                        _cap_sheet_output(instance)
                    if tool_name == "gmail":
                        _fix_gmail_html_body(instance)
                    instances.append(instance)
                    continue

                # Custom tools: load from file path via importlib.util
                if entry.module_path.startswith("vandelay_custom_"):
                    loaded_mod = sys.modules.get(entry.module_path)
                    if loaded_mod is None:
                        import importlib.util as ilu

                        from vandelay.config.constants import CUSTOM_TOOLS_DIR

                        file_path = CUSTOM_TOOLS_DIR / f"{entry.name}.py"
                        spec = ilu.spec_from_file_location(
                            entry.module_path, file_path,
                        )
                        if spec and spec.loader:
                            loaded_mod = ilu.module_from_spec(spec)
                            sys.modules[entry.module_path] = loaded_mod
                            spec.loader.exec_module(loaded_mod)
                    if loaded_mod:
                        custom_cls = getattr(loaded_mod, entry.class_name)
                        instances.append(custom_cls())
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
