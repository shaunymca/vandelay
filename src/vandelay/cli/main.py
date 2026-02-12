"""Vandelay CLI — the main entry point."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from vandelay import __version__
from vandelay.cli.cron_commands import app as cron_app
from vandelay.cli.daemon import app as daemon_app
from vandelay.cli.knowledge_commands import app as knowledge_app
from vandelay.cli.tools_commands import app as tools_app

app = typer.Typer(
    name="vandelay",
    help="Always-on AI assistant powered by Agno.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(tools_app, name="tools")
app.add_typer(cron_app, name="cron")
app.add_typer(knowledge_app, name="knowledge")
app.add_typer(daemon_app, name="daemon")
console = Console()

# Background server state
_server_handle: dict = {}


@app.callback(invoke_without_command=True)
def version_callback(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    if version:
        from vandelay.cli.banner import print_banner

        print_banner(console, compact=True)
        console.print(f"  [dim]v{__version__}[/dim]")
        raise typer.Exit()


@app.command()
def onboard(
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n",
        help="Headless setup from environment variables (for PaaS/CI)",
    ),
):
    """Run the interactive setup wizard."""
    if non_interactive:
        from vandelay.cli.onboard import run_headless_onboarding

        try:
            settings = run_headless_onboarding()
        except ValueError as e:
            console.print(f"[red]Headless onboarding failed: {e}[/red]")
            raise typer.Exit(1) from None
        console.print(f"[green]\u2713[/green] Headless onboarding complete — {settings.agent_name}")
    else:
        from vandelay.cli.onboard import run_onboarding

        try:
            settings = run_onboarding()
        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled.[/yellow]")
            raise typer.Exit(1) from None

    # Drop straight into chat after onboarding
    asyncio.run(_run_with_server(settings))


@app.command()
def start(
    server_only: bool = typer.Option(
        False, "--server", "-s",
        help="Server only — no terminal chat (for headless/daemon deployments)",
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w",
        help="Auto-restart on file changes (watches src, config, workspace)",
    ),
):
    """Start your agent with the API server and terminal chat."""
    import os

    from vandelay.config.settings import Settings, get_settings

    if watch:
        os.environ["VANDELAY_AUTO_RESTART"] = "1"

    if not Settings.config_exists():
        # Auto-onboard if VANDELAY_AUTO_ONBOARD=1 is set (PaaS use case)
        if os.environ.get("VANDELAY_AUTO_ONBOARD", "").lower() in ("1", "true", "yes"):
            from vandelay.cli.onboard import run_headless_onboarding

            try:
                settings = run_headless_onboarding()
                console.print(
                    f"[green]\u2713[/green] Auto-onboarded — {settings.agent_name}"
                )
            except ValueError as e:
                console.print(f"[red]Auto-onboarding failed: {e}[/red]")
                raise typer.Exit(1) from None
        else:
            console.print(
                "[yellow]No config found.[/yellow] "
                "Run [bold]vandelay onboard[/bold] first."
            )
            raise typer.Exit(1)
    else:
        settings = get_settings()

    if server_only:
        _start_server_foreground(settings)
    else:
        asyncio.run(_run_with_server(settings))


@app.command()
def status():
    """Show current configuration and agent status."""
    from vandelay.config.settings import Settings, get_settings

    if not Settings.config_exists():
        console.print("[yellow]Not configured.[/yellow] Run [bold]vandelay onboard[/bold] first.")
        raise typer.Exit(1)

    settings = get_settings()
    running = _is_server_running(settings.server.host, settings.server.port)
    _show_status(settings, server_running=running)


def _show_status(settings, server_running: bool = False) -> None:
    """Print current config summary."""
    console.print()
    console.print(f"  [bold]Agent:[/bold]     {settings.agent_name}")
    model_str = f"{settings.model.provider} / {settings.model.model_id}"
    console.print(f"  [bold]Model:[/bold]     {model_str}")
    console.print(f"  [bold]Safety:[/bold]    {settings.safety.mode}")
    console.print(f"  [bold]Timezone:[/bold]  {settings.timezone}")
    console.print(f"  [bold]DB:[/bold]        {settings.db_path}")
    console.print(f"  [bold]Workspace:[/bold] {settings.workspace_dir}")

    channels = []
    if settings.channels.telegram_enabled:
        channels.append("Telegram")
    if settings.channels.whatsapp_enabled:
        channels.append("WhatsApp")
    ch_str = ", ".join(channels) if channels else "Terminal only"
    console.print(f"  [bold]Channels:[/bold]  {ch_str}")
    knowledge_str = "enabled" if settings.knowledge.enabled else "disabled"
    console.print(f"  [bold]Knowledge:[/bold] {knowledge_str}")

    if settings.team.enabled:
        members = ", ".join(settings.team.members)
        console.print(f"  [bold]Team:[/bold]      [green]enabled[/green] ({members})")
    else:
        console.print("  [bold]Team:[/bold]      [dim]disabled[/dim]")

    if server_running or _server_handle.get("running"):
        host = settings.server.host
        port = settings.server.port
        console.print(f"  [bold]Server:[/bold]   [green]running[/green] at http://{host}:{port}")
        console.print(f"  [bold]Docs:[/bold]     http://{host}:{port}/docs")
        console.print(f"  [bold]WS:[/bold]       ws://{host}:{port}/ws/terminal")
    else:
        console.print("  [bold]Server:[/bold]   [dim]not running[/dim]")

    console.print()


def _show_help() -> None:
    """Print available slash commands."""
    console.print()
    console.print("[bold]Commands:[/bold]")
    console.print("  [bold]/help[/bold]      — Show this help")
    console.print("  [bold]/status[/bold]    — Show current configuration + server info")
    console.print("  [bold]/config[/bold]    — Change settings")
    console.print("  [bold]/new[/bold]       — Start a new chat session")
    console.print("  [bold]/quit[/bold]      — Exit the chat")
    console.print()


def _run_config(settings):
    """Open the config menu and return updated settings."""
    from vandelay.cli.onboard import run_config_menu

    return run_config_menu(settings)


def _is_server_running(host: str, port: int) -> bool:
    """Check if a Vandelay server is already responding on host:port."""
    import socket

    # Use localhost for connection check when bound to 0.0.0.0
    check_host = "127.0.0.1" if host == "0.0.0.0" else host
    try:
        with socket.create_connection((check_host, port), timeout=1):
            return True
    except OSError:
        # If configured host is unavailable (e.g. Tailscale down), try localhost
        if check_host != "127.0.0.1":
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return True
            except OSError:
                pass
        return False


def _start_background_server(settings) -> None:
    """Start the FastAPI server in a background thread."""
    import threading

    import uvicorn

    from vandelay.server.app import create_app

    app_instance = create_app(settings)

    config = uvicorn.Config(
        app_instance,
        host=settings.server.host,
        port=settings.server.port,
        access_log=False,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    # Store for shutdown
    _server_handle["server"] = server
    _server_handle["running"] = True

    def _run():
        server.run()
        _server_handle["running"] = False

    thread = threading.Thread(target=_run, daemon=True, name="vandelay-server")
    thread.start()
    _server_handle["thread"] = thread


def _stop_background_server() -> None:
    """Signal the background server to shut down."""
    server = _server_handle.get("server")
    if server:
        server.should_exit = True
    thread = _server_handle.get("thread")
    if thread:
        thread.join(timeout=5)
    _server_handle.clear()


def _start_server_foreground(settings) -> None:
    """Launch the FastAPI server in the foreground (headless/daemon mode)."""
    import uvicorn

    from vandelay.cli.banner import print_banner

    print_banner(console, compact=True)
    console.print(f"  [dim]v{__version__}[/dim]")
    _show_status(settings, server_running=True)

    from vandelay.server.app import create_app

    uvicorn.run(
        create_app(settings),
        host=settings.server.host,
        port=settings.server.port,
        access_log=False,
    )


async def _run_with_server(settings) -> None:
    """Start the server in the background, then run terminal chat."""
    from vandelay.agents.factory import create_agent, create_team
    from vandelay.channels.base import IncomingMessage
    from vandelay.cli.banner import print_agent_ready
    from vandelay.core import ChatService, RefAgentProvider

    host = settings.server.host
    port = settings.server.port
    external_server = _is_server_running(host, port)

    if external_server:
        # Server already running (e.g. daemon) — just launch terminal chat
        console.print(f"  [dim]Server already running on port {port} — connecting...[/dim]")
    else:
        # Start our own server in background thread
        _start_background_server(settings)
        await asyncio.sleep(0.5)

    # Print banner with server info
    print_agent_ready(console, settings.agent_name, __version__)
    console.print(f"  [dim]Server running at http://{host}:{port}[/dim]")
    console.print(f"  [dim]AgentOS playground at http://{host}:{port}/docs[/dim]")
    if settings.team.enabled:
        console.print(f"  [dim]Team mode: {len(settings.team.members)} specialists[/dim]")
    console.print()

    # Create agent/team for terminal chat (shares DB with server's agent)
    # Use a list so the reload callback can swap the reference
    agent_ref: list = [None]
    team_mode = settings.team.enabled

    def _create_agent_or_team(**kwargs):
        if team_mode:
            return create_team(settings, **kwargs)
        return create_agent(settings, **kwargs)

    def _reload_agent() -> None:
        """Recreate the terminal agent/team in-place after tool changes."""
        console.print("[dim]Reloading agent with updated tools...[/dim]")
        agent_ref[0] = _create_agent_or_team(reload_callback=_reload_agent)

    agent_ref[0] = _create_agent_or_team(reload_callback=_reload_agent)

    # ChatService with lazy provider — always uses the current agent_ref[0]
    chat_service = ChatService(RefAgentProvider(agent_ref))

    session_id = "terminal"
    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ")
        except (KeyboardInterrupt, EOFError):
            break

        text = user_input.strip()
        if not text:
            continue

        # --- Slash commands ---
        cmd = text.lower()

        if cmd in ("/quit", "/exit", "quit", "exit"):
            break

        if cmd == "/help":
            _show_help()
            continue

        if cmd == "/status":
            _show_status(settings)
            continue

        if cmd == "/config":
            try:
                settings = await asyncio.to_thread(_run_config, settings)
                team_mode = settings.team.enabled
                agent_ref[0] = _create_agent_or_team(reload_callback=_reload_agent)
                console.print(f"\n[bold blue]{settings.agent_name}[/bold blue] is ready.\n")
            except KeyboardInterrupt:
                console.print("\n[yellow]Config cancelled — keeping current settings.[/yellow]\n")
            continue

        if cmd == "/new":
            import uuid

            session_id = f"terminal-{uuid.uuid4().hex[:8]}"
            console.print("\n[dim]New session started.[/dim]\n")
            continue

        # --- Regular chat ---
        incoming = IncomingMessage(
            text=text,
            session_id=session_id,
            channel="terminal",
        )

        with console.status(
            f"[bold blue]{settings.agent_name}[/bold blue] is thinking...",
            spinner="dots",
        ):
            result = await chat_service.run(incoming)

        console.print(f"\n[bold blue]{settings.agent_name}:[/bold blue] ", end="")
        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")
        elif result.content:
            console.print(result.content)
        else:
            console.print("[dim](no response)[/dim]")

        console.print()

    # Graceful shutdown — only stop the server if we started it
    if not external_server:
        console.print("\n[dim]Shutting down server...[/dim]")
        _stop_background_server()
    console.print(f"[dim]{settings.agent_name} signing off.[/dim]")
