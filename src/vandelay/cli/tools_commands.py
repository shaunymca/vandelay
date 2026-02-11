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
