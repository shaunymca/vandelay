"""CLI commands for knowledge base management."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="knowledge",
    help="Manage the knowledge base — add documents, list, clear, status.",
    no_args_is_help=True,
)
console = Console()

# Supported file extensions for knowledge ingestion
SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".csv", ".json", ".docx", ".doc",
}

_MEMBER_HELP = (
    "Team member name to target their private knowledge base "
    "(e.g. --member cto). Omit to use the shared knowledge base."
)


def _get_settings():
    from vandelay.config.settings import get_settings

    return get_settings()


def _ensure_knowledge(member_name: str | None = None):
    """Return (knowledge, vector_db) or exit with an error.

    Args:
        member_name: When provided, opens the per-member collection.
            ``None`` opens the shared collection.
    """
    settings = _get_settings()

    if not settings.knowledge.enabled:
        console.print(
            "[yellow]Knowledge is not enabled.[/yellow] "
            "Run [bold]vandelay onboard[/bold] or set knowledge.enabled=true in config."
        )
        raise typer.Exit(1)

    from vandelay.knowledge.setup import create_knowledge

    knowledge = create_knowledge(settings, member_name=member_name)
    if knowledge is None:
        console.print(
            "[red]Could not initialise knowledge.[/red] "
            "Check embedder and vector DB configuration "
            "(run [bold]vandelay knowledge status[/bold] for details)."
        )
        raise typer.Exit(1)

    return knowledge, knowledge.vector_db


def _load_documents(file_path: Path) -> list:
    """Load documents from a file using the appropriate reader."""
    from agno.knowledge.document import Document

    text = file_path.read_text(encoding="utf-8", errors="replace")

    # Return a simple Document — Knowledge.load() will handle chunking
    return [Document(name=file_path.name, content=text)]


def _find_supported_files(path: Path) -> list[Path]:
    """Recursively find supported files under a directory."""
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [path]
        return []

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(path.rglob(f"*{ext}"))
    return sorted(files)


@app.command("add")
def add_document(
    path: str = typer.Argument(help="File or directory path to add to the knowledge base"),
    member: Optional[str] = typer.Option(None, "--member", "-m", help=_MEMBER_HELP),
):
    """Load a file or directory into the knowledge base."""
    target = Path(path).resolve()

    if not target.exists():
        console.print(f"[red]Path not found: {target}[/red]")
        raise typer.Exit(1)

    files = _find_supported_files(target)
    if not files:
        console.print(
            f"[yellow]No supported files found.[/yellow] "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
        raise typer.Exit(1)

    label = f"'{member}'" if member else "shared"
    console.print(f"  Adding to [bold]{label}[/bold] knowledge base…")

    knowledge, _vector_db = _ensure_knowledge(member_name=member)

    total_docs = 0
    for file_path in files:
        try:
            docs = _load_documents(file_path)
            knowledge.load(documents=docs, upsert=True)
            total_docs += len(docs)
            console.print(f"  [green]\u2713[/green] {file_path.name}")
        except Exception as e:
            console.print(f"  [red]\u2717[/red] {file_path.name}: {e}")

    console.print(f"\n  [bold]Added {total_docs} document(s) from {len(files)} file(s).[/bold]")


@app.command("list")
def list_documents(
    member: Optional[str] = typer.Option(None, "--member", "-m", help=_MEMBER_HELP),
):
    """Show loaded documents and vector count."""
    knowledge, vector_db = _ensure_knowledge(member_name=member)

    from vandelay.knowledge.vectordb import get_vector_count

    count = get_vector_count(vector_db)
    label = f"'{member}'" if member else "shared"

    if count == 0:
        console.print(f"[dim]No documents in the {label} knowledge base.[/dim]")
        hint = f"vandelay knowledge add --member {member} <path>" if member else "vandelay knowledge add <path>"
        console.print(f"[dim]Add some: {hint}[/dim]")
        raise typer.Exit()

    table = Table(title=f"Knowledge Base ({label})", show_lines=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Vector count", str(count))

    from vandelay.config.constants import VANDELAY_HOME

    db_path = VANDELAY_HOME / "data" / "knowledge_vectors"
    table.add_row("Storage path", str(db_path))

    console.print(table)


@app.command("clear")
def clear_knowledge(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    member: Optional[str] = typer.Option(None, "--member", "-m", help=_MEMBER_HELP),
):
    """Remove all vectors from the knowledge base (fresh start)."""
    label = f"'{member}'" if member else "shared"
    if not confirm:
        proceed = typer.confirm(f"This will delete all vectors from the {label} knowledge base. Continue?")
        if not proceed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    _knowledge, vector_db = _ensure_knowledge(member_name=member)

    try:
        if hasattr(vector_db, "drop"):
            vector_db.drop()
        console.print(f"[green]\u2713[/green] {label.capitalize()} knowledge base cleared.")
    except Exception as e:
        console.print(f"[red]Error clearing knowledge base: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("status")
def knowledge_status():
    """Show embedder, vector DB path, and document count for all collections."""
    from vandelay.knowledge.vectordb import is_knowledge_supported

    settings = _get_settings()

    console.print()

    if not is_knowledge_supported():
        console.print(
            "  [bold]Supported:[/bold]  [yellow]no[/yellow]  "
            "(Intel Mac x86_64 — no vector DB wheels available)"
        )
        console.print(
            "\n  [dim]Neither chromadb nor lancedb ships pre-built wheels for macOS x86_64.\n"
            "  Knowledge is unavailable on this platform without building from source.[/dim]"
        )
        console.print()
        return

    enabled = settings.knowledge.enabled
    status = "[green]yes[/green]" if enabled else "[dim]no[/dim]"
    console.print(f"  [bold]Enabled:[/bold]    {status}")

    if not enabled:
        console.print(
            "\n  [dim]Enable with: vandelay onboard or set knowledge.enabled=true in config[/dim]"
        )
        return

    # Embedder info
    ecfg = settings.knowledge.embedder
    provider = ecfg.provider or settings.model.provider
    console.print(f"  [bold]Embedder:[/bold]   {provider}")
    if ecfg.model:
        console.print(f"  [bold]Model:[/bold]      {ecfg.model}")

    from vandelay.config.constants import VANDELAY_HOME

    db_path = VANDELAY_HOME / "data" / "knowledge_vectors"
    console.print(f"  [bold]Vector DB:[/bold]  {db_path}")

    # Vector counts: shared + per-member
    try:
        from vandelay.knowledge.setup import create_knowledge
        from vandelay.knowledge.vectordb import get_vector_count

        def _count_label(member_name: str | None, label: str) -> None:
            k = create_knowledge(settings, member_name=member_name)
            if k is None:
                console.print(f"  [bold]{label}:[/bold]    [yellow]unavailable[/yellow]")
                return
            count = get_vector_count(k.vector_db)
            console.print(f"  [bold]{label}:[/bold]    {count} vector(s)")

        _count_label(None, "Vectors (shared)")
        for entry in settings.team.members:
            name = entry if isinstance(entry, str) else entry.name
            _count_label(name, f"Vectors ({name})")

    except Exception:
        console.print("  [bold]Vectors:[/bold]    [dim]unknown (DB not initialized)[/dim]")

    # Corpus version info
    from vandelay.knowledge.corpus import _get_stored_versions

    stored = _get_stored_versions()
    if stored:
        console.print(
            f"  [bold]Corpus:[/bold]     "
            f"agno={stored.get('agno', '?')}, vandelay={stored.get('vandelay', '?')}"
        )
    else:
        console.print("  [bold]Corpus:[/bold]     [dim]not indexed yet[/dim]")

    knowledge_dir = Path(settings.workspace_dir) / "knowledge"
    if knowledge_dir.exists():
        file_count = sum(1 for f in knowledge_dir.rglob("*") if f.is_file())
        console.print(f"  [bold]Files:[/bold]      {file_count} in {knowledge_dir}")
    else:
        console.print(f"  [bold]Files:[/bold]      [dim]{knowledge_dir} (not created yet)[/dim]")

    console.print()


@app.command("refresh")
def refresh_corpus(
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-index even if versions match"
    ),
):
    """Re-index the built-in Vandelay Expert documentation corpus."""
    import asyncio

    knowledge, _vector_db = _ensure_knowledge()

    from vandelay.knowledge.corpus import corpus_needs_refresh, index_corpus

    if not force and not corpus_needs_refresh():
        console.print("[dim]Corpus is already up to date.[/dim]")
        raise typer.Exit()

    console.print("[bold]Indexing Agno documentation corpus...[/bold]")
    count = asyncio.run(index_corpus(knowledge, force=force))
    console.print(f"\n  [green]✓[/green] Indexed {count} source(s).")
