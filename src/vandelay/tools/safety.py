"""Safety guard for shell tools — enforces trust/confirm/tiered modes."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from agno.tools import Toolkit

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


class SafeShellTools(Toolkit):
    """Wraps shell command execution with safety checks.

    Modes:
        trust   — all commands execute immediately
        confirm — all commands require agent to note they ran (no blocking in agent context)
        tiered  — safe commands run freely, risky ones get flagged
    """

    def __init__(
        self,
        mode: str = "confirm",
        allowed_commands: list[str] | None = None,
        blocked_patterns: list[str] | None = None,
        timeout: int = 120,
    ) -> None:
        super().__init__(name="safe_shell")
        self.mode = mode
        self.allowed_commands = allowed_commands or []
        self.blocked_patterns = blocked_patterns or []
        self.timeout = timeout

        self.register(self._run_command_tool)
        self.register(self._check_safety_tool)

    def _run_command_tool(self, command: str) -> str:
        """Execute a shell command. Respects the configured safety mode."""
        return self.run_command(command)

    def _check_safety_tool(self, command: str) -> str:
        """Check if a command would be allowed by the safety system."""
        return self.check_safety(command)

    def run_command(self, command: str) -> str:
        """Execute a shell command with safety checks applied."""
        block_reason = self._check_blocked(command)
        if block_reason:
            return f"BLOCKED: {block_reason}"

        if self.mode == "trust":
            return self._execute(command)

        if self.mode == "tiered":
            if self._is_safe_command(command):
                return self._execute(command)
            else:
                return (
                    f"NEEDS APPROVAL: The command `{command}` is not in the safe list. "
                    f"In tiered mode, only these commands run freely: "
                    f"{', '.join(self.allowed_commands[:10])}..."
                )

        # confirm mode — execute but note it
        result = self._execute(command)
        return f"[confirm mode] Executed: `{command}`\n\n{result}"

    def check_safety(self, command: str) -> str:
        """Check if a command is safe to run without executing it."""
        block_reason = self._check_blocked(command)
        if block_reason:
            return f"BLOCKED: {block_reason}"

        if self.mode == "trust":
            return "ALLOWED: Trust mode — all non-blocked commands are allowed."

        if self.mode == "tiered":
            if self._is_safe_command(command):
                return "ALLOWED: Command is in the safe list."
            return "NEEDS APPROVAL: Command is not in the safe list."

        return "ALLOWED (with confirmation): Command will execute with a note in confirm mode."

    def _check_blocked(self, command: str) -> str | None:
        """Check if command matches any blocked pattern."""
        cmd_lower = command.lower().strip()
        for pattern in self.blocked_patterns:
            if pattern.lower() in cmd_lower:
                return f"Command matches blocked pattern: `{pattern}`"
        return None

    def _is_safe_command(self, command: str) -> bool:
        """Check if command starts with an allowed command."""
        cmd_stripped = command.strip()
        for allowed in self.allowed_commands:
            if cmd_stripped == allowed or cmd_stripped.startswith(allowed + " "):
                return True
        return False

    def _execute(self, command: str) -> str:
        """Actually run the command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return f"ERROR: Command timed out after {self.timeout}s."
        except Exception as e:
            return f"ERROR: {e}"


def create_safe_shell_tools(settings: Settings) -> SafeShellTools:
    """Factory: create SafeShellTools configured from settings."""
    return SafeShellTools(
        mode=settings.safety.mode,
        allowed_commands=settings.safety.allowed_commands,
        blocked_patterns=settings.safety.blocked_patterns,
        timeout=settings.safety.command_timeout_seconds,
    )
