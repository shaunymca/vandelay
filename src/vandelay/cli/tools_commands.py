"""CLI commands for tool management: list, add, remove, refresh."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="tools",
    help="Manage agent tools — list, add, remove, refresh.",
    no_args_is_help=True,
)
console = Console()


def _get_settings():
    from vandelay.config.settings import Settings, get_settings

    if not Settings.config_exists():
        console.print("[yellow]Not configured.[/yellow] Run [bold]vandelay onboard[/bold] first.")
        raise typer.Exit(1)
    return get_settings()


def _get_manager():
    from vandelay.tools.manager import ToolManager

    return ToolManager()


@app.command("list")
def list_tools(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    builtin_only: bool = typer.Option(False, "--builtin", "-b", help="Show only built-in tools"),
    enabled_only: bool = typer.Option(False, "--enabled", "-e", help="Show only enabled tools"),
):
    """List all available Agno tools."""
    settings = _get_settings()
    manager = _get_manager()

    tools = manager.list_tools(
        enabled_tools=settings.enabled_tools,
        category=category,
    )

    if builtin_only:
        tools = [t for t in tools if t["is_builtin"]]
    if enabled_only:
        tools = [t for t in tools if t["enabled"]]

    if not tools:
        console.print("[dim]No tools found matching your filters.[/dim]")
        raise typer.Exit()

    table = Table(title="Agno Tools", show_lines=False)
    table.add_column("Name", style="bold")
    table.add_column("Category", style="dim")
    table.add_column("Status")
    table.add_column("Deps", style="dim")

    for t in tools:
        # Status column
        if t["enabled"]:
            if t["installed"]:
                status = "[green]enabled[/green]"
            else:
                status = "[yellow]enabled (deps missing)[/yellow]"
        else:
            if t["is_builtin"]:
                status = "[dim]available[/dim]"
            elif t["installed"]:
                status = "[dim]available (installed)[/dim]"
            else:
                status = "[dim]available[/dim]"

        deps = ", ".join(t["pip_dependencies"]) if t["pip_dependencies"] else "built-in"

        table.add_row(t["name"], t["category"], status, deps)

    console.print(table)
    console.print(f"\n  [dim]{len(tools)} tools shown. "
                  f"{sum(1 for t in tools if t['enabled'])} enabled.[/dim]")

    # Show categories hint
    if not category:
        cats = sorted(set(t["category"] for t in tools))
        console.print(f"  [dim]Categories: {', '.join(cats)}[/dim]")
        console.print("  [dim]Filter: vandelay tools list --category search[/dim]\n")


@app.command("add")
def add_tool(
    name: str = typer.Argument(help="Tool name to enable (e.g. 'shell', 'duckduckgo')"),
    skip_install: bool = typer.Option(False, "--no-install", help="Enable without installing deps"),
):
    """Enable a tool and install its dependencies."""
    settings = _get_settings()
    manager = _get_manager()

    entry = manager.registry.get(name)
    if entry is None:
        console.print(f"[red]Unknown tool: {name}[/red]")
        console.print("[dim]Run `vandelay tools list` to see available tools.[/dim]")
        raise typer.Exit(1)

    # Install dependencies if needed
    if not skip_install and not entry.is_builtin:
        console.print(f"  Installing dependencies for [bold]{name}[/bold]...")
        result = manager.install_deps(name)
        if result.success:
            console.print(f"  [green]✓[/green] {result.message}")
        else:
            console.print(f"  [red]✗[/red] {result.message}")
            console.print("[dim]You can retry or use --no-install to skip.[/dim]")
            raise typer.Exit(1)

    # Enable in settings
    if name not in settings.enabled_tools:
        settings.enabled_tools.append(name)
        settings.save()
        console.print(f"  [green]✓[/green] [bold]{name}[/bold] ({entry.class_name}) enabled.")
    else:
        console.print(f"  [dim]{name} is already enabled.[/dim]")

    console.print("  [dim]Restart your agent to activate the tool.[/dim]")


@app.command("remove")
def remove_tool(
    name: str = typer.Argument(help="Tool name to disable"),
    uninstall: bool = typer.Option(False, "--uninstall", "-u", help="Also remove pip dependencies"),
):
    """Disable a tool (optionally uninstall its dependencies)."""
    settings = _get_settings()
    manager = _get_manager()

    if name not in settings.enabled_tools:
        console.print(f"[dim]{name} is not currently enabled.[/dim]")
        raise typer.Exit()

    settings.enabled_tools.remove(name)
    settings.save()
    console.print(f"  [green]✓[/green] [bold]{name}[/bold] disabled.")

    if uninstall:
        result = manager.uninstall_deps(name)
        if result.success:
            console.print(f"  [green]✓[/green] {result.message}")
        else:
            console.print(f"  [yellow]⚠[/yellow] {result.message}")

    console.print("  [dim]Restart your agent for changes to take effect.[/dim]")


_GOOGLE_TOKEN_FILE = "google_token.json"

# All scopes needed across Google tools (broadest per API — no redundant readonly)
_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Tools that use Google OAuth and need token_path + port override
_GOOGLE_OAUTH_TOOLS = {
    "gmail": {"token_kwarg": "token_path", "port_kwarg": "port"},
    "google_drive": {"token_kwarg": "token_path", "port_kwarg": "auth_port"},
    "googlecalendar": {"token_kwarg": "token_path", "port_kwarg": "oauth_port"},
    "googlesheets": {"token_kwarg": "token_path", "port_kwarg": "oauth_port"},
}


@app.command("auth-google")
def auth_google(
    reauth: bool = typer.Option(
        False, "--reauth", "-r", help="Re-authenticate even if token exists",
    ),
):
    """Authenticate Google services (Gmail, Calendar, Drive, Sheets)."""
    import os

    from vandelay.config.constants import VANDELAY_HOME

    token_path = VANDELAY_HOME / _GOOGLE_TOKEN_FILE

    if token_path.exists() and not reauth:
        console.print(f"  [dim]Token already exists at {token_path}[/dim]")
        console.print("  [dim]Run with --reauth to re-authenticate.[/dim]")
        raise typer.Exit()

    # Load .env so Google credentials are available
    from vandelay.agents.factory import _load_env
    _load_env()

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    project_id = os.environ.get("GOOGLE_PROJECT_ID")

    if not all([client_id, client_secret, project_id]):
        console.print("[red]Missing Google OAuth credentials.[/red]")
        console.print("  Set these in ~/.vandelay/.env:")
        console.print("    GOOGLE_CLIENT_ID=...")
        console.print("    GOOGLE_CLIENT_SECRET=...")
        console.print("    GOOGLE_PROJECT_ID=...")
        raise typer.Exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        console.print("[red]Google auth libraries not installed.[/red]")
        console.print(
            "  Run: uv add google-api-python-client"
            " google-auth-httplib2 google-auth-oauthlib"
        )
        raise typer.Exit(1) from None

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": (
                "https://www.googleapis.com/oauth2/v1/certs"
            ),
            "redirect_uris": [
                "urn:ietf:wg:oauth:2.0:oob",
                "http://localhost",
            ],
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config, _GOOGLE_SCOPES,
    )

    # Use console-based flow (no browser needed on server)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(prompt="consent")

    console.print()
    console.print("[bold]Google OAuth Setup[/bold]")
    console.print()
    console.print("  Scopes: Gmail, Calendar, Drive, Sheets")
    console.print()
    console.print("1. Open this URL in your browser:")
    console.print(f"   [link]{auth_url}[/link]")
    console.print()
    console.print("2. Sign in and authorize access")
    console.print("3. Copy the authorization code and paste it below")
    console.print()

    code = input("Authorization code: ").strip()
    if not code:
        console.print("[red]No code provided.[/red]")
        raise typer.Exit(1)

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_path.write_text(creds.to_json())
        console.print(
            f"  [green]\u2713[/green] Google authenticated."
            f" Token saved to {token_path}"
        )
        console.print(
            "  [dim]Covers: Gmail, Calendar, Drive, Sheets[/dim]"
        )
    except Exception as e:
        console.print(f"  [red]\u2717[/red] OAuth failed: {e}")
        raise typer.Exit(1) from None


@app.command("browse")
def browse_tools():
    """Interactively browse, inspect, and enable/disable tools."""
    settings = _get_settings()
    interactive_tools_browser(settings)


def interactive_tools_browser(settings) -> None:
    """Interactive tools browser with filter → list → detail → action flow.

    Called from both ``vandelay tools browse`` and the config menu.
    """
    import questionary

    manager = _get_manager()

    while True:
        # --- Step 1: Filter selection ---
        all_tools = manager.list_tools(enabled_tools=settings.enabled_tools)
        enabled_count = sum(1 for t in all_tools if t["enabled"])
        available_count = len(all_tools) - enabled_count

        filter_choice = questionary.select(
            "How would you like to browse tools?",
            choices=[
                questionary.Choice(
                    title=f"Enabled tools ({enabled_count})", value="enabled",
                ),
                questionary.Choice(
                    title=f"All tools ({len(all_tools)})", value="all",
                ),
                questionary.Choice(
                    title=f"Available tools ({available_count})", value="available",
                ),
                questionary.Choice(title="Back", value="back"),
            ],
        ).ask()

        if filter_choice is None or filter_choice == "back":
            break

        # Apply filter
        if filter_choice == "enabled":
            filtered = [t for t in all_tools if t["enabled"]]
        elif filter_choice == "available":
            filtered = [t for t in all_tools if not t["enabled"]]
        else:
            filtered = all_tools

        if not filtered:
            console.print("  [dim]No tools match this filter.[/dim]")
            continue

        # --- Step 2: Tool list ---
        while True:
            tool_choices = []
            for t in sorted(filtered, key=lambda x: x["name"]):
                status = "enabled" if t["enabled"] else "available"
                label = f"{t['name']} [{t['category']}] - {status}"
                tool_choices.append(questionary.Choice(title=label, value=t["name"]))
            tool_choices.append(questionary.Choice(title="<- Back to filter", value="back"))

            selected = questionary.select(
                "Select a tool to learn more:",
                choices=tool_choices,
            ).ask()

            if selected is None or selected == "back":
                break

            # --- Step 3: Tool detail + action ---
            entry = manager.registry.get(selected)
            if entry is None:
                continue

            is_enabled = selected in settings.enabled_tools
            installed = manager._check_installed(entry)

            console.print()
            console.print(f"  [bold]Name:[/bold]       {entry.name}")
            console.print(f"  [bold]Class:[/bold]      {entry.class_name}")
            console.print(f"  [bold]Category:[/bold]   {entry.category}")
            deps_str = ", ".join(entry.pip_dependencies) or "none"
            console.print(f"  [bold]Deps:[/bold]       {deps_str}")
            inst = "[green]yes[/green]" if installed else "[red]no[/red]"
            enab = "[green]enabled[/green]" if is_enabled else "[dim]not enabled[/dim]"
            console.print(f"  [bold]Installed:[/bold]  {inst}")
            console.print(f"  [bold]Status:[/bold]     {enab}")
            if entry.description:
                desc = entry.description
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                console.print(f"  [bold]Info:[/bold]       {desc}")
            console.print()

            # Build action choices
            action_choices = []
            if is_enabled:
                action_choices.append(
                    questionary.Choice(title="Disable this tool", value="disable")
                )
            else:
                action_choices.append(
                    questionary.Choice(title="Enable this tool", value="enable")
                )
            action_choices.append(
                questionary.Choice(title="Back to list", value="back")
            )

            action = questionary.select(
                "What would you like to do?",
                choices=action_choices,
            ).ask()

            if action == "enable":
                if not entry.is_builtin:
                    console.print(
                        f"  Installing dependencies for [bold]{selected}[/bold]..."
                    )
                    result = manager.install_deps(selected)
                    if result.success:
                        console.print(f"  [green]✓[/green] {result.message}")
                    else:
                        console.print(f"  [red]✗[/red] {result.message}")
                        continue
                settings.enabled_tools.append(selected)
                settings.save()
                console.print(
                    f"  [green]✓[/green] [bold]{selected}[/bold] enabled."
                )
                # Update the filtered list to reflect the change
                for t in filtered:
                    if t["name"] == selected:
                        t["enabled"] = True

            elif action == "disable":
                settings.enabled_tools.remove(selected)
                settings.save()
                console.print(
                    f"  [green]✓[/green] [bold]{selected}[/bold] disabled."
                )
                for t in filtered:
                    if t["name"] == selected:
                        t["enabled"] = False


@app.command("refresh")
def refresh_registry():
    """Rebuild the tool registry from the installed Agno package."""
    manager = _get_manager()

    console.print("  Scanning agno.tools package...")
    count = manager.refresh()
    console.print(f"  [green]✓[/green] Registry refreshed: [bold]{count}[/bold] tools discovered.")

    from vandelay.config.constants import TOOL_REGISTRY_FILE
    console.print(f"  [dim]Cache: {TOOL_REGISTRY_FILE}[/dim]")


@app.command("info")
def tool_info(
    name: str = typer.Argument(help="Tool name to inspect"),
):
    """Show details about a specific tool."""
    manager = _get_manager()
    settings = _get_settings()

    entry = manager.registry.get(name)
    if entry is None:
        console.print(f"[red]Unknown tool: {name}[/red]")
        raise typer.Exit(1)

    enabled = name in settings.enabled_tools
    installed = manager._check_installed(entry)

    console.print()
    console.print(f"  [bold]Name:[/bold]       {entry.name}")
    console.print(f"  [bold]Class:[/bold]      {entry.class_name}")
    console.print(f"  [bold]Module:[/bold]     {entry.module_path}")
    console.print(f"  [bold]Category:[/bold]   {entry.category}")
    console.print(f"  [bold]Built-in:[/bold]   {'yes' if entry.is_builtin else 'no'}")
    console.print(f"  [bold]Deps:[/bold]       {', '.join(entry.pip_dependencies) or 'none'}")
    inst = "[green]yes[/green]" if installed else "[red]no[/red]"
    enab = "[green]yes[/green]" if enabled else "[dim]no[/dim]"
    console.print(f"  [bold]Installed:[/bold]  {inst}")
    console.print(f"  [bold]Enabled:[/bold]    {enab}")
    console.print()
