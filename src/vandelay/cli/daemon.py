"""Daemon management — systemd (Linux) and launchd (macOS) service control."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import typer
from rich.console import Console

from vandelay.config.constants import LOGS_DIR, VANDELAY_HOME

app = typer.Typer(
    name="daemon",
    help="Manage Vandelay as a system service (Linux systemd / macOS launchd).",
    no_args_is_help=True,
)
console = Console()

# --- Paths ---

_SYSTEMD_UNIT = Path.home() / ".config" / "systemd" / "user" / "vandelay.service"
_LAUNCHD_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.vandelay.agent.plist"
_LOG_FILE = LOGS_DIR / "vandelay.log"


# --- Helpers ---

def _platform() -> str:
    """Return 'linux', 'darwin', or 'windows'."""
    return platform.system().lower()


def _find_vandelay_executable() -> str:
    """Resolve the vandelay CLI entry point."""
    exe = shutil.which("vandelay")
    if exe:
        return exe
    # Fallback: python -m vandelay.cli.main
    return f"{sys.executable} -m vandelay.cli.main"


def _ensure_log_dir() -> None:
    """Create the logs directory if it doesn't exist."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


# --- systemd (Linux) ---

def _systemd_unit_content(exe: str) -> str:
    """Generate a systemd user unit file."""
    return textwrap.dedent(f"""\
        [Unit]
        Description=Vandelay AI Agent
        After=network.target

        [Service]
        Type=simple
        ExecStart={exe} start --server
        Restart=on-failure
        RestartSec=5
        StandardOutput=append:{_LOG_FILE}
        StandardError=append:{_LOG_FILE}
        WorkingDirectory={VANDELAY_HOME}

        [Install]
        WantedBy=default.target
    """)


def _systemd_install(exe: str) -> None:
    _ensure_log_dir()
    _SYSTEMD_UNIT.parent.mkdir(parents=True, exist_ok=True)
    _SYSTEMD_UNIT.write_text(_systemd_unit_content(exe), encoding="utf-8")
    _run(["systemctl", "--user", "daemon-reload"])
    _run(["systemctl", "--user", "enable", "vandelay"])
    console.print(f"[green]Installed[/green] systemd unit: {_SYSTEMD_UNIT}")
    console.print("[dim]Start with: vandelay daemon start[/dim]")


def _systemd_uninstall() -> None:
    _run(["systemctl", "--user", "disable", "vandelay"], check=False)
    _run(["systemctl", "--user", "stop", "vandelay"], check=False)
    if _SYSTEMD_UNIT.exists():
        _SYSTEMD_UNIT.unlink()
    _run(["systemctl", "--user", "daemon-reload"])
    console.print("[green]Uninstalled[/green] systemd unit.")


def _systemd_start() -> None:
    result = _run(["systemctl", "--user", "start", "vandelay"], check=False)
    if result.returncode == 0:
        console.print("[green]Started[/green] vandelay service.")
    else:
        console.print(f"[red]Failed to start:[/red] {result.stderr.strip()}")


def _systemd_stop() -> None:
    result = _run(["systemctl", "--user", "stop", "vandelay"], check=False)
    if result.returncode == 0:
        console.print("[green]Stopped[/green] vandelay service.")
    else:
        console.print(f"[red]Failed to stop:[/red] {result.stderr.strip()}")


def _systemd_restart() -> None:
    result = _run(["systemctl", "--user", "restart", "vandelay"], check=False)
    if result.returncode == 0:
        console.print("[green]Restarted[/green] vandelay service.")
    else:
        console.print(f"[red]Failed to restart:[/red] {result.stderr.strip()}")


def _systemd_status() -> None:
    result = _run(["systemctl", "--user", "status", "vandelay"], check=False)
    console.print(result.stdout or result.stderr or "[dim]No status available.[/dim]")


def _systemd_logs() -> None:
    import contextlib

    with contextlib.suppress(KeyboardInterrupt):
        subprocess.run(
            ["journalctl", "--user-unit", "vandelay", "-f", "-n", "50"],
            check=False,
        )


# --- launchd (macOS) ---

def _launchd_plist_content(exe: str) -> str:
    """Generate a launchd plist file."""
    # Split exe into program + arguments for ProgramArguments
    parts = exe.split()
    args_xml = "\n".join(f"        <string>{p}</string>" for p in parts)
    args_xml += "\n        <string>start</string>"
    args_xml += "\n        <string>--server</string>"

    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
          "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>com.vandelay.agent</string>
            <key>ProgramArguments</key>
            <array>
        {args_xml}
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <true/>
            <key>StandardOutPath</key>
            <string>{_LOG_FILE}</string>
            <key>StandardErrorPath</key>
            <string>{_LOG_FILE}</string>
            <key>WorkingDirectory</key>
            <string>{VANDELAY_HOME}</string>
        </dict>
        </plist>
    """)


def _launchd_install(exe: str) -> None:
    _ensure_log_dir()
    _LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    _LAUNCHD_PLIST.write_text(_launchd_plist_content(exe), encoding="utf-8")
    console.print(f"[green]Installed[/green] launchd plist: {_LAUNCHD_PLIST}")
    console.print("[dim]Start with: vandelay daemon start[/dim]")


def _launchd_uninstall() -> None:
    if _LAUNCHD_PLIST.exists():
        _run(["launchctl", "unload", str(_LAUNCHD_PLIST)], check=False)
        _LAUNCHD_PLIST.unlink()
    console.print("[green]Uninstalled[/green] launchd plist.")


def _launchd_start() -> None:
    if not _LAUNCHD_PLIST.exists():
        console.print("[red]Plist not found.[/red] Run [bold]vandelay daemon install[/bold] first.")
        raise typer.Exit(1)
    result = _run(["launchctl", "load", str(_LAUNCHD_PLIST)], check=False)
    if result.returncode == 0:
        console.print("[green]Started[/green] vandelay service.")
    else:
        console.print(f"[red]Failed to start:[/red] {result.stderr.strip()}")


def _launchd_stop() -> None:
    if not _LAUNCHD_PLIST.exists():
        console.print("[dim]Service not installed.[/dim]")
        return
    result = _run(["launchctl", "unload", str(_LAUNCHD_PLIST)], check=False)
    if result.returncode == 0:
        console.print("[green]Stopped[/green] vandelay service.")
    else:
        console.print(f"[red]Failed to stop:[/red] {result.stderr.strip()}")


def _launchd_restart() -> None:
    _launchd_stop()
    _launchd_start()


def _launchd_status() -> None:
    result = _run(["launchctl", "list"], check=False)
    lines = [line for line in result.stdout.splitlines() if "vandelay" in line.lower()]
    if lines:
        console.print("\n".join(lines))
    else:
        console.print("[dim]vandelay service not found in launchctl list.[/dim]")


def _launchd_logs() -> None:
    import contextlib

    if not _LOG_FILE.exists():
        console.print(f"[dim]No log file at {_LOG_FILE}[/dim]")
        return

    with contextlib.suppress(KeyboardInterrupt):
        subprocess.run(["tail", "-f", "-n", "50", str(_LOG_FILE)], check=False)


# --- Dispatch ---

def _unsupported() -> None:
    console.print(
        "[yellow]Daemon management is not supported on Windows.[/yellow]\n"
        "Use [bold]vandelay start --server[/bold] to run in the foreground,\n"
        "or set up a Windows service manually with NSSM or Task Scheduler."
    )
    raise typer.Exit(1)


# --- Public API (used by onboarding) ---

def install_daemon_service() -> bool:
    """Install daemon service. Returns True on success, False if unsupported/failed."""
    plat = _platform()
    if plat not in ("linux", "darwin"):
        return False

    try:
        exe = _find_vandelay_executable()
        if plat == "linux":
            _systemd_install(exe)
        else:
            _launchd_install(exe)
        return True
    except Exception as exc:
        console.print(f"[red]Daemon install failed:[/red] {exc}")
        return False


def is_daemon_supported() -> bool:
    """Return True if the current platform supports daemon installation."""
    return _platform() in ("linux", "darwin")


# --- Commands ---

@app.command()
def install():
    """Install Vandelay as a system service."""
    plat = _platform()
    exe = _find_vandelay_executable()

    if plat == "linux":
        _systemd_install(exe)
    elif plat == "darwin":
        _launchd_install(exe)
    else:
        _unsupported()


@app.command()
def uninstall():
    """Remove the Vandelay system service."""
    plat = _platform()

    if plat == "linux":
        _systemd_uninstall()
    elif plat == "darwin":
        _launchd_uninstall()
    else:
        _unsupported()


@app.command()
def start():
    """Start the Vandelay service."""
    plat = _platform()

    if plat == "linux":
        if not _SYSTEMD_UNIT.exists():
            console.print(
                "[red]Service not installed.[/red] "
                "Run [bold]vandelay daemon install[/bold] first."
            )
            raise typer.Exit(1)
        _systemd_start()
    elif plat == "darwin":
        _launchd_start()
    else:
        _unsupported()


@app.command()
def stop():
    """Stop the Vandelay service."""
    plat = _platform()

    if plat == "linux":
        _systemd_stop()
    elif plat == "darwin":
        _launchd_stop()
    else:
        _unsupported()


@app.command()
def restart():
    """Restart the Vandelay service."""
    plat = _platform()

    if plat == "linux":
        _systemd_restart()
    elif plat == "darwin":
        _launchd_restart()
    else:
        _unsupported()


@app.command()
def status():
    """Show Vandelay service status."""
    plat = _platform()

    if plat == "linux":
        _systemd_status()
    elif plat == "darwin":
        _launchd_status()
    else:
        _unsupported()


@app.command()
def logs():
    """Tail the Vandelay service logs."""
    plat = _platform()

    if plat == "linux":
        _systemd_logs()
    elif plat == "darwin":
        _launchd_logs()
    else:
        _unsupported()
