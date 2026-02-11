"""CLI commands for cron job management."""

from __future__ import annotations

from datetime import UTC

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="cron",
    help="Manage scheduled cron jobs — list, add, remove, pause, resume.",
    no_args_is_help=True,
)
console = Console()


def _get_store(path=None):
    """Create a CronJobStore (works without a running server)."""
    from vandelay.scheduler.store import CronJobStore

    return CronJobStore(path=path)


@app.command("list")
def list_jobs():
    """List all scheduled cron jobs."""
    store = _get_store()
    jobs = store.all()

    if not jobs:
        console.print("[dim]No cron jobs configured.[/dim]")
        console.print(
            '[dim]Add one: vandelay cron add "Job name" "*/5 * * * *" "do something"[/dim]'
        )
        raise typer.Exit()

    table = Table(title="Cron Jobs", show_lines=False)
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Name", style="bold")
    table.add_column("Schedule")
    table.add_column("Status")
    table.add_column("Type", style="dim")
    table.add_column("Runs", justify="right")
    table.add_column("Command", max_width=40)

    for job in jobs:
        status = "[green]enabled[/green]" if job.enabled else "[yellow]paused[/yellow]"
        table.add_row(
            job.id,
            job.name,
            job.cron_expression,
            status,
            job.job_type.value,
            str(job.run_count),
            job.command[:40] + ("..." if len(job.command) > 40 else ""),
        )

    console.print(table)
    console.print(f"\n  [dim]{len(jobs)} jobs total.[/dim]\n")


@app.command("add")
def add_job(
    name: str = typer.Argument(help="Human-readable job name"),
    cron_expression: str = typer.Argument(help="5-field cron expression (e.g. '*/5 * * * *')"),
    command: str = typer.Argument(help="Natural language command for the agent"),
    timezone: str = typer.Option("UTC", "--tz", "-t", help="Timezone for the schedule"),
):
    """Add a new cron job. It will be picked up on the next server start."""
    from croniter import croniter

    from vandelay.scheduler.models import CronJob

    if not croniter.is_valid(cron_expression):
        console.print(f"[red]Invalid cron expression: {cron_expression}[/red]")
        console.print("[dim]Use standard 5-field format: minute hour day month weekday[/dim]")
        console.print("[dim]Examples: '0 9 * * *' (daily 9am), '*/30 * * * *' (every 30min)[/dim]")
        raise typer.Exit(1)

    store = _get_store()
    job = CronJob(
        name=name,
        cron_expression=cron_expression,
        command=command,
        timezone=timezone,
    )

    # Compute next_run
    from datetime import datetime

    cron = croniter(cron_expression)
    job.next_run = cron.get_next(datetime).replace(tzinfo=UTC)

    store.add(job)

    console.print(f"  [green]\\u2713[/green] Added job [bold]{name}[/bold] (ID: {job.id})")
    console.print(f"  [dim]Schedule: {cron_expression} ({timezone})[/dim]")
    console.print(f"  [dim]Command: {command}[/dim]")
    console.print("  [dim]Will be active on next server start.[/dim]")


@app.command("remove")
def remove_job(
    job_id: str = typer.Argument(help="Job ID to remove"),
):
    """Remove a cron job permanently."""
    store = _get_store()

    if store.remove(job_id):
        console.print(f"  [green]\\u2713[/green] Removed job [bold]{job_id}[/bold].")
    else:
        console.print(f"[red]Job '{job_id}' not found.[/red]")
        raise typer.Exit(1)


@app.command("pause")
def pause_job(
    job_id: str = typer.Argument(help="Job ID to pause"),
):
    """Pause a cron job without deleting it."""
    store = _get_store()
    job = store.get(job_id)

    if job is None:
        console.print(f"[red]Job '{job_id}' not found.[/red]")
        raise typer.Exit(1)

    if not job.enabled:
        console.print(f"[dim]Job '{job.name}' is already paused.[/dim]")
        raise typer.Exit()

    job.enabled = False
    store.update(job)
    console.print(f"  [green]\\u2713[/green] Paused [bold]{job.name}[/bold] (ID: {job_id}).")
    console.print(f"  [dim]Use 'vandelay cron resume {job_id}' to re-enable.[/dim]")


@app.command("resume")
def resume_job(
    job_id: str = typer.Argument(help="Job ID to resume"),
):
    """Resume a paused cron job."""
    store = _get_store()
    job = store.get(job_id)

    if job is None:
        console.print(f"[red]Job '{job_id}' not found.[/red]")
        raise typer.Exit(1)

    if job.enabled:
        console.print(f"[dim]Job '{job.name}' is already running.[/dim]")
        raise typer.Exit()

    job.enabled = True

    # Recompute next_run
    from datetime import datetime

    from croniter import croniter

    cron = croniter(job.cron_expression)
    job.next_run = cron.get_next(datetime).replace(tzinfo=UTC)

    store.update(job)
    console.print(f"  [green]\\u2713[/green] Resumed [bold]{job.name}[/bold] (ID: {job_id}).")
