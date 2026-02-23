"""Status tab — live server metrics pulled from /health and /status."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import httpx
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static


def _fmt_uptime(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    h, rem = divmod(td.seconds, 3600)
    m, s = divmod(rem, 60)
    if td.days:
        return f"{td.days}d {h}h {m}m"
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


_METRICS: list[tuple[str, str]] = [
    ("server",    "Server"),
    ("agent",     "Agent"),
    ("model",     "Model"),
    ("safety",    "Safety mode"),
    ("timezone",  "Timezone"),
    ("uptime",    "Uptime"),
    ("version",   "Version"),
    ("channels",  "Channels"),
    ("traces",    "Traces"),
    ("heartbeat", "Heartbeat"),
]


class StatusTab(Widget):
    """Live server status — polls /health and /status every 5 s."""

    DEFAULT_CSS = """
    StatusTab {
        height: 1fr;
    }
    #status-outer {
        height: 1fr;
        padding: 2 4;
    }
    #status-heading {
        color: #58a6ff;
        text-style: bold;
        height: 1;
        margin-bottom: 2;
    }
    #status-offline {
        color: #8b949e;
        text-style: italic;
        height: 1;
    }
    .metric-row {
        height: 1;
        margin-bottom: 1;
    }
    .metric-key {
        width: 18;
        color: #8b949e;
    }
    .metric-val {
        color: #c9d1d9;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._host = "127.0.0.1"
        self._port = 8000
        self._load_server_settings()

    def _load_server_settings(self) -> None:
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
        with Vertical(id="status-outer"):
            yield Static("● Server Status", id="status-heading")
            yield Static(
                "[bold red]Not Running[/bold red]  — press Start in the header to begin.",
                id="status-offline",
            )
            for key, label in _METRICS:
                with Horizontal(classes="metric-row", id=f"row-{key}"):
                    yield Static(f"{label}", classes="metric-key")
                    yield Static("—", classes="metric-val", id=f"val-{key}")

    def on_mount(self) -> None:
        self._set_online(False)
        self.set_interval(5, self._refresh)
        self.call_after_refresh(self._refresh)

    def _set_online(self, online: bool) -> None:
        self.query_one("#status-offline").display = not online
        for row in self.query(".metric-row"):
            row.display = online

    def _server_mode(self) -> str:
        """Return 'daemon' if the daemon is running, 'foreground' otherwise."""
        try:
            from vandelay.cli.daemon import is_daemon_running

            return "daemon" if is_daemon_running() else "foreground"
        except Exception:
            return "foreground"

    async def _refresh(self) -> None:
        base = f"http://{self._host}:{self._port}"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                h_resp, s_resp = await asyncio.gather(
                    client.get(f"{base}/health"),
                    client.get(f"{base}/status"),
                    return_exceptions=True,
                )

            if isinstance(h_resp, Exception) or isinstance(s_resp, Exception):
                self._set_online(False)
                return

            health = h_resp.json()
            status = s_resp.json()

            self._set_online(True)

            provider = status.get("model_provider", "")
            model_id = status.get("model_id", "")
            model_str = f"{provider} / {model_id}" if provider else model_id

            channels = status.get("channels", [])
            channels_str = ", ".join(channels) if channels else "none"

            mode = self._server_mode()
            server_str = f"[bold green]Running[/bold green]  ({mode})"

            # Read heartbeat from local config (always accurate regardless of server state)
            try:
                from vandelay.config.settings import get_settings
                hb = get_settings().heartbeat
                if hb.enabled:
                    hb_str = (
                        f"[green]ON[/green]  every {hb.interval_minutes}min"
                        f"  ·  {hb.active_hours_start}:00–{hb.active_hours_end}:00"
                    )
                else:
                    hb_str = "[dim]off[/dim]"
            except Exception:
                hb_str = "—"

            updates: dict[str, str] = {
                "server":    server_str,
                "agent":     health.get("agent_name", "—"),
                "model":     model_str or "—",
                "safety":    status.get("safety_mode", "—"),
                "timezone":  status.get("timezone", "—"),
                "uptime":    _fmt_uptime(health.get("uptime_seconds", 0)),
                "version":   health.get("version", "—"),
                "channels":  channels_str,
                "traces":    str(status.get("total_traces", 0)),
                "heartbeat": hb_str,
            }
            for key, val in updates.items():
                self.query_one(f"#val-{key}", Static).update(val)

        except Exception:
            self._set_online(False)
