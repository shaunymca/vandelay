"""CLI commands for memory management."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="memory",
    help="Manage agent memory (workspace files and native DB).",
    no_args_is_help=True,
)
console = Console()


@app.command()
def status():
    """Show current memory state — DB memories and any archived file entries."""
    from vandelay.config.settings import Settings, get_settings

    if not Settings.config_exists():
        console.print("[yellow]Not configured.[/yellow] Run [bold]vandelay onboard[/bold] first.")
        raise typer.Exit(1)

    settings = get_settings()

    # Count DB memories
    from vandelay.memory.setup import create_db

    db = create_db(settings)
    user_id = settings.user_id or "default"
    db_memories = db.get_user_memories(user_id=user_id)
    db_count = len(db_memories) if db_memories else 0

    # Check for imported memories
    imported = []
    if db_memories:
        imported = [
            m for m in db_memories
            if m.topics and "imported_from_workspace" in m.topics
        ]

    # Check if MEMORY.md still has entries (pre-migration archive)
    from pathlib import Path

    from vandelay.core.memory_migration import parse_memory_entries

    memory_path = Path(settings.workspace_dir) / "MEMORY.md"
    file_entries = 0
    if memory_path.exists():
        content = memory_path.read_text(encoding="utf-8")
        file_entries = len(parse_memory_entries(content))

    console.print()
    console.print("[bold]Memory Status[/bold]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")

    table.add_row("DB memories (total)", str(db_count))
    table.add_row("DB memories (from file import)", str(len(imported)))

    if file_entries > 0:
        table.add_row(
            "MEMORY.md (archive)",
            f"[yellow]{file_entries} entries[/yellow] — will be auto-migrated on next server start",
        )

    console.print(table)
    console.print()


@app.command()
def migrate(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Migrate MEMORY.md entries into Agno's native memory DB."""
    from pathlib import Path

    from vandelay.config.settings import Settings, get_settings
    from vandelay.core.memory_migration import (
        check_migration_needed,
        migrate_memory_to_db,
        parse_memory_entries,
    )

    if not Settings.config_exists():
        console.print("[yellow]Not configured.[/yellow] Run [bold]vandelay onboard[/bold] first.")
        raise typer.Exit(1)

    settings = get_settings()

    if not check_migration_needed(settings):
        console.print("[green]Nothing to migrate.[/green] MEMORY.md has no entries.")
        raise typer.Exit()

    # Preview entries
    memory_path = Path(settings.workspace_dir) / "MEMORY.md"
    content = memory_path.read_text(encoding="utf-8")
    entries = parse_memory_entries(content)

    console.print()
    console.print(f"[bold]Found {len(entries)} entries to migrate:[/bold]")
    console.print()
    for i, entry in enumerate(entries, 1):
        ts = f" [{entry.timestamp}]" if entry.timestamp else ""
        section = f" ({entry.section})" if entry.section else ""
        console.print(f"  {i}. {entry.content}{ts}{section}")
    console.print()

    if not yes:
        confirm = typer.confirm("Proceed with migration?")
        if not confirm:
            console.print("[yellow]Migration cancelled.[/yellow]")
            raise typer.Exit()

    from vandelay.memory.setup import create_db

    db = create_db(settings)
    result = migrate_memory_to_db(settings, db=db)

    console.print()
    console.print(f"[green]Migrated {result.imported} entries to native memory.[/green]")
    if result.archived:
        console.print(f"[dim]Original archived to {result.archived}[/dim]")
    console.print("[dim]MEMORY.md reset to header.[/dim]")
    console.print()
