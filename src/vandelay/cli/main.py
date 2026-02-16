"""Vandelay CLI — the main entry point."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from vandelay import __version__
from vandelay.cli.cron_commands import app as cron_app
from vandelay.cli.daemon import app as daemon_app
from vandelay.cli.knowledge_commands import app as knowledge_app
from vandelay.cli.memory_commands import app as memory_app
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
app.add_typer(memory_app, name="memory")
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
    asyncio.run(_run_with_server(settings, first_run=True))


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
def config():
    """Open the interactive configuration menu."""
    from vandelay.config.settings import Settings, get_settings

    if not Settings.config_exists():
        console.print("[yellow]Not configured.[/yellow] Run [bold]vandelay onboard[/bold] first.")
        raise typer.Exit(1)

    settings = get_settings()
    from vandelay.cli.onboard import run_config_menu

    try:
        run_config_menu(settings, exit_label="Done")
    except KeyboardInterrupt:
        console.print("\n[dim]Config closed.[/dim]")


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
        members = ", ".join(
            m if isinstance(m, str) else m.name for m in settings.team.members
        )
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


def _render_markdown(console: Console, text: str) -> None:
    """Render a string as Rich Markdown in the terminal."""
    from rich.markdown import Markdown
    from rich.padding import Padding

    md = Markdown(text.strip())
    console.print(Padding(md, (0, 0, 0, 2)))


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
    """Check if something is already listening on the given port."""
    import socket

    # Try connecting to the configured host, then localhost as fallback
    check_hosts = ["127.0.0.1"] if host == "0.0.0.0" else [host, "127.0.0.1"]

    for h in check_hosts:
        try:
            with socket.create_connection((h, port), timeout=2):
                return True
        except OSError:
            continue

    # Last resort: check if the port is bound by any process (Linux)
    # This catches the case where the server is starting up but not yet accepting
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind(("0.0.0.0", port))
        s.close()
        # Bind succeeded → port is free
        return False
    except OSError:
        # Bind failed → port is in use
        return True


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


async def _run_with_server(settings, *, first_run: bool = False) -> None:
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
        console.print(f"  [dim]Server already running on port {port} — entering chat only.[/dim]")
    else:
        # Start our own server in background thread
        _start_background_server(settings)
        await asyncio.sleep(0.5)

        # Verify server actually started (might have failed to bind)
        if not _server_handle.get("running"):
            console.print(
                f"[yellow]Could not start server on port {port}.[/yellow] "
                "Continuing in chat-only mode."
            )
            external_server = True

    # Print banner with server info
    print_agent_ready(console, settings.agent_name, __version__)
    if not external_server:
        console.print(f"  [dim]Server running at http://{host}:{port}[/dim]")
        console.print(f"  [dim]AgentOS playground at http://{host}:{port}/docs[/dim]")
    if settings.team.enabled:
        console.print(f"  [dim]Team mode: {len(settings.team.members)} specialists[/dim]")
    console.print()

    # The background server thread creates agno's global httpx.AsyncClient
    # singleton with HTTP/2 enabled. HTTP/2 uses asyncio.Event objects that are
    # loop-bound, so the terminal (running on a DIFFERENT event loop) can't
    # reuse that client. Simply setting it to None causes a race — the server
    # thread recreates it on its own loop before the terminal gets to use it.
    #
    # Fix: replace the global client with one using http2=False. HTTP/1.1
    # doesn't use asyncio primitives, so both threads can safely share it.
    import httpx

    import agno.utils.http as _agno_http
    from agno.utils.http import _async_client_lock

    def _reset_agno_http_client() -> None:
        """Replace agno's global async client with an HTTP/1.1 client."""
        with _async_client_lock:
            old = _agno_http._global_async_client
            _agno_http._global_async_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=1000, max_keepalive_connections=200,
                ),
                http2=False,
                follow_redirects=True,
            )
            # Don't await aclose on old — server thread may still reference it,
            # and it'll be GC'd. The important thing is the global is now safe.

    _reset_agno_http_client()

    # Create agent/team for terminal chat
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

    # Clean up sessions with mismatched user_id to prevent silent upsert failures
    from vandelay.memory.setup import cleanup_stale_sessions, create_db as _create_db

    _db = _create_db(settings)
    cleanup_stale_sessions(_db, settings.user_id or "default")

    agent_ref[0] = _create_agent_or_team(reload_callback=_reload_agent)

    # ChatService with lazy provider — always uses the current agent_ref[0]
    chat_service = ChatService(RefAgentProvider(agent_ref))

    session_id = "terminal"

    # First-run welcome — LLM-generated greeting with timeout fallback
    if first_run:
        name = settings.agent_name
        welcome_prompt = (
            "You've just been set up for the first time. "
            "Say hi in exactly 2 short sentences: who you are and "
            "one thing the user should try first. No more than 40 words total."
        )
        welcome_msg = IncomingMessage(
            text=welcome_prompt,
            session_id=session_id,
            user_id=settings.user_id or "default",
            channel="terminal",
        )
        _fallback = (
            f"Hey! I'm {name}, your AI assistant. "
            "Ask me anything, or type /help to see what I can do."
        )
        response_parts: list[str] = []
        try:
            async with asyncio.timeout(30):
                async for chunk in chat_service.run_chunked(welcome_msg):
                    if chunk.error:
                        break
                    if chunk.content:
                        response_parts.append(chunk.content)
        except (TimeoutError, Exception):
            pass

        welcome_text = "".join(response_parts).strip() or _fallback
        console.print(f"\n[bold blue]{name}:[/bold blue]")
        _render_markdown(console, welcome_text)
        console.print()

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
            user_id=settings.user_id or "default",
            channel="terminal",
        )

        console.print(f"\n[bold blue]{settings.agent_name}:[/bold blue]")
        response_parts: list[str] = []
        had_error = False
        async for chunk in chat_service.run_chunked(incoming):
            if chunk.error:
                console.print(f"  [red]Error: {chunk.error}[/red]")
                had_error = True
                break
            if chunk.content:
                response_parts.append(chunk.content)

        if response_parts and not had_error:
            _render_markdown(console, "".join(response_parts))
        console.print()

    # Graceful shutdown — only stop the server if we started it.
    # Suppress OpenTelemetry "Failed to detach context" tracebacks that fire
    # when Ctrl+C interrupts a streaming response mid-flight.
    import io
    import sys

    sys.stderr = io.StringIO()

    if not external_server:
        console.print("\n[dim]Shutting down server...[/dim]")
        _stop_background_server()
    console.print(f"[dim]{settings.agent_name} signing off.[/dim]")

    sys.stderr = sys.__stderr__
