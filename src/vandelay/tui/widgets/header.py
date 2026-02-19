"""VandelayHeader — fixed header with ASCII art left, status + controls right."""

from __future__ import annotations

import asyncio
import socket
import subprocess
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static

WORDMARK = """\
    ╦  ╦╔═╗╔╗╔╔╦╗╔═╗╦  ╔═╗╦ ╦
    ╚╗╔╝╠═╣║║║ ║║║╣ ║  ╠═╣╚╦╝
    ╚╝ ╩ ╩╝╚╝═╩╝╚═╝╩═╝╩ ╩ ╩"""

TAGLINE = "The employee who doesn't exist."

ServerState = Literal["online", "offline", "transitioning"]

_LIGHT: dict[str, str] = {
    "online":        "[bold green]●[/bold green]",
    "offline":       "[bold red]●[/bold red]",
    "transitioning": "[bold yellow]●[/bold yellow]",
}

_LABEL: dict[str, str] = {
    "online":        "Online",
    "offline":       "Offline",
    "transitioning": "…",
}


class VandelayHeader(Widget):
    """Left: ASCII art + tagline. Right: status light + server control buttons."""

    server_state: reactive[ServerState] = reactive("offline")

    def __init__(self) -> None:
        super().__init__()
        self._host = "127.0.0.1"
        self._port = 8000
        self._load_settings()

    def _load_settings(self) -> None:
        try:
            from vandelay.config.settings import Settings, get_settings

            if Settings.config_exists():
                s = get_settings()
                host = s.server.host
                self._host = "127.0.0.1" if host == "0.0.0.0" else host
                self._port = s.server.port
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        # Left: brand + status dot
        with Vertical(id="header-brand"):
            yield Static(WORDMARK, id="wordmark")
            yield Static(TAGLINE, id="tagline")
            yield Static("", id="status-light")

        # Right: server control buttons only
        with Vertical(id="header-controls"):
            with Horizontal(id="btn-row"):
                yield Button("Start",   id="btn-start",   variant="success")
                yield Button("Restart", id="btn-restart", variant="warning")
                yield Button("Stop",    id="btn-stop",    variant="error")

    def on_mount(self) -> None:
        self._apply_state(self.server_state)
        self.set_interval(3, self._poll_server)
        self.call_after_refresh(self._poll_server)


    # ── Polling ───────────────────────────────────────────────────────────

    async def _poll_server(self) -> None:
        # Skip poll during transitioning — let the action settle first
        if self.server_state == "transitioning":
            return
        loop = asyncio.get_event_loop()
        reachable = await loop.run_in_executor(None, self._check_server)
        self.server_state = "online" if reachable else "offline"

    def _check_server(self) -> bool:
        try:
            with socket.create_connection((self._host, self._port), timeout=1):
                return True
        except OSError:
            return False

    # ── Reactive watch ────────────────────────────────────────────────────

    def watch_server_state(self, state: ServerState) -> None:
        self._apply_state(state)

    def _apply_state(self, state: ServerState) -> None:
        try:
            light = self.query_one("#status-light", Static)
            light.update(f"{_LIGHT[state]}  {_LABEL[state]}")

            online = state == "online"
            transitioning = state == "transitioning"

            self.query_one("#btn-start").display   = not online and not transitioning
            self.query_one("#btn-restart").display = online
            self.query_one("#btn-stop").display    = online
        except Exception:
            pass

    # ── Button handlers ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "btn-start":   self._do_start,
            "btn-restart": self._do_restart,
            "btn-stop":    self._do_stop,
        }
        handler = handlers.get(event.button.id or "")
        if handler:
            handler()

    def _do_start(self) -> None:
        self.server_state = "transitioning"
        try:
            subprocess.Popen(
                ["vandelay", "start", "--server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.app.notify("Server starting…", severity="information", timeout=4)
        except Exception as exc:
            self.server_state = "offline"
            self.app.notify(f"Failed to start server: {exc}", severity="error")

    def _do_restart(self) -> None:
        self.server_state = "transitioning"
        try:
            from vandelay.cli.daemon import is_daemon_running, restart_daemon

            if is_daemon_running():
                ok = restart_daemon()
                msg = "Daemon restarting…" if ok else "Daemon restart failed."
                sev = "information" if ok else "error"
                self.app.notify(msg, severity=sev, timeout=4)
            else:
                self._do_stop()
                self._do_start()
        except Exception as exc:
            self.server_state = "offline"
            self.app.notify(f"Restart failed: {exc}", severity="error")

    def _do_stop(self) -> None:
        self.server_state = "transitioning"
        try:
            from vandelay.cli.daemon import is_daemon_running

            if is_daemon_running():
                subprocess.run(
                    ["vandelay", "daemon", "stop"],
                    capture_output=True,
                    timeout=10,
                )
                self.app.notify("Daemon stopped.", severity="information", timeout=4)
            else:
                self._kill_port()
        except Exception as exc:
            self.app.notify(f"Stop failed: {exc}", severity="error")

    def _kill_port(self) -> None:
        """Kill the process bound to the server port (non-daemon fallback)."""
        import sys

        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["netstat", "-ano"], capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.splitlines():
                    if f":{self._port}" in line and "LISTENING" in line:
                        pid = line.split()[-1]
                        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                        break
            else:
                subprocess.run(
                    ["fuser", "-k", f"{self._port}/tcp"], capture_output=True, timeout=5
                )
            self.app.notify("Server stopped.", severity="information", timeout=4)
        except Exception:
            self.app.notify(
                f"Could not stop server on port {self._port}.", severity="warning"
            )
