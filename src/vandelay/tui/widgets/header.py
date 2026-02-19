"""VandelayHeader — fixed header with server status, controls, and ASCII art."""

from __future__ import annotations

import asyncio
import socket
import subprocess

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


class VandelayHeader(Widget):
    """Custom header: server status + controls + ASCII art brand."""

    server_online: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self._host = "127.0.0.1"
        self._port = 8000
        self._agent_label = "Vandelay"
        self._model_label = ""
        self._load_settings()

    def _load_settings(self) -> None:
        try:
            from vandelay.config.settings import Settings, get_settings

            if Settings.config_exists():
                s = get_settings()
                host = s.server.host
                self._host = "127.0.0.1" if host == "0.0.0.0" else host
                self._port = s.server.port
                self._agent_label = s.agent_name
                self._model_label = f"{s.model.provider}/{s.model.model_id}"
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        with Vertical(id="header-left"):
            yield Static("", id="status-line")
            with Horizontal(id="btn-row"):
                yield Button("  Start  ", id="btn-start", variant="success")
                yield Button(" Restart ", id="btn-restart", variant="warning")
                yield Button("  Stop   ", id="btn-stop", variant="error")
        with Vertical(id="header-brand"):
            yield Static(WORDMARK, id="wordmark")
            yield Static(TAGLINE, id="tagline")

    def on_mount(self) -> None:
        # Initial button visibility before first poll
        self._set_buttons(self.server_online)
        self._update_status_line(self.server_online)
        # Start polling
        self.set_interval(3, self._poll_server)
        # Fire an immediate poll
        self.call_after_refresh(self._poll_server)

    async def _poll_server(self) -> None:
        loop = asyncio.get_event_loop()
        online = await loop.run_in_executor(None, self._check_server)
        self.server_online = online

    def _check_server(self) -> bool:
        try:
            with socket.create_connection((self._host, self._port), timeout=1):
                return True
        except OSError:
            return False

    def watch_server_online(self, online: bool) -> None:
        self._set_buttons(online)
        self._update_status_line(online)

    def _update_status_line(self, online: bool) -> None:
        try:
            indicator = self.query_one("#status-line", Static)
            if online:
                model_part = f"  [dim]{self._model_label}[/dim]" if self._model_label else ""
                indicator.update(
                    f"[bold green]●[/bold green] Online  "
                    f"[bold]{self._agent_label}[/bold]{model_part}"
                )
            else:
                indicator.update("[bold red]●[/bold red]  [dim]Server offline[/dim]")
        except Exception:
            pass

    def _set_buttons(self, online: bool) -> None:
        try:
            self.query_one("#btn-start").display = not online
            self.query_one("#btn-restart").display = online
            self.query_one("#btn-stop").display = online
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-start":
            self._do_start()
        elif btn == "btn-restart":
            self._do_restart()
        elif btn == "btn-stop":
            self._do_stop()

    def _do_start(self) -> None:
        try:
            subprocess.Popen(
                ["vandelay", "start", "--server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.app.notify("Server starting…", severity="information", timeout=4)
        except Exception as exc:
            self.app.notify(f"Failed to start server: {exc}", severity="error")

    def _do_restart(self) -> None:
        try:
            from vandelay.cli.daemon import is_daemon_running, restart_daemon

            if is_daemon_running():
                ok = restart_daemon()
                if ok:
                    self.app.notify("Daemon restarting…", severity="information", timeout=4)
                else:
                    self.app.notify("Daemon restart failed.", severity="error")
            else:
                # No daemon — kill the port and restart
                self._do_stop()
                self._do_start()
        except Exception as exc:
            self.app.notify(f"Restart failed: {exc}", severity="error")

    def _do_stop(self) -> None:
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
                # Kill whatever is listening on the port
                self._kill_port()
        except Exception as exc:
            self.app.notify(f"Stop failed: {exc}", severity="error")

    def _kill_port(self) -> None:
        """Kill the process bound to the server port (non-daemon fallback)."""
        import sys

        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if f":{self._port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                        break
            else:
                subprocess.run(
                    ["fuser", "-k", f"{self._port}/tcp"],
                    capture_output=True,
                    timeout=5,
                )
            self.app.notify("Server stopped.", severity="information", timeout=4)
        except Exception:
            self.app.notify(
                f"Could not stop server on port {self._port}.",
                severity="warning",
            )
