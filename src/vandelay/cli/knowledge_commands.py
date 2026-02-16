"""CLI commands for knowledge base management."""

from __future__ import annotations

from pathlib import Path

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


def _get_settings():
    from vandelay.config.settings import get_settings

    return get_settings()


def _ensure_knowledge():
    """Return (knowledge, vector_db) or exit with an error."""
    settings = _get_settings()

    if not settings.knowledge.enabled:
        console.print(
            "[yellow]Knowledge is not enabled.[/yellow] "
            "Run [bold]vandelay onboard[/bold] or set knowledge.enabled=true in config."
        )
        raise typer.Exit(1)

    from vandelay.knowledge.embedder import create_embedder

    embedder = create_embedder(settings)
    if embedder is None:
        console.print(
            "[red]No embedder available.[/red] "
            "Set knowledge.embedder.provider in config "
            "or ensure your model provider supports embeddings."
        )
        raise typer.Exit(1)

    try:
        from agno.vectordb.lancedb import LanceDb
    except ImportError:
        console.print("[red]lancedb not installed.[/red] Run: uv add lancedb")
        raise typer.Exit(1) from None

    from vandelay.config.constants import VANDELAY_HOME

    vector_db = LanceDb(
        uri=str(VANDELAY_HOME / "data" / "knowledge_vectors"),
        table_name="vandelay_knowledge",
        embedder=embedder,
    )

    try:
        from agno.knowledge.knowledge import Knowledge
    except ImportError:
        console.print("[red]agno knowledge package not available.[/red]")
        raise typer.Exit(1) from None

    knowledge = Knowledge(name="vandelay-knowledge", vector_db=vector_db)
    return knowledge, vector_db


def _load_documents(file_path: Path) -> list:
    """Load documents from a file using the appropriate reader."""
    from agno.document import Document

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

    knowledge, vector_db = _ensure_knowledge()

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
def list_documents():
    """Show loaded documents and vector count."""
    knowledge, vector_db = _ensure_knowledge()

    try:
        # LanceDb exposes table info
        if hasattr(vector_db, "table") and vector_db.table is not None:
            count = vector_db.table.count_rows()
        elif hasattr(vector_db, "_table") and vector_db._table is not None:
            count = vector_db._table.count_rows()
        else:
            # Try to access via search with empty query to trigger table creation
            count = 0
    except Exception:
        count = 0

    if count == 0:
        console.print("[dim]No documents in the knowledge base.[/dim]")
        console.print("[dim]Add some: vandelay knowledge add <path>[/dim]")
        raise typer.Exit()

    table = Table(title="Knowledge Base", show_lines=False)
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
):
    """Remove all vectors from the knowledge base (fresh start)."""
    if not confirm:
        proceed = typer.confirm("This will delete all knowledge vectors. Continue?")
        if not proceed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    _knowledge, vector_db = _ensure_knowledge()

    try:
        if hasattr(vector_db, "drop"):
            vector_db.drop()
        console.print("[green]\u2713[/green] Knowledge base cleared.")
    except Exception as e:
        console.print(f"[red]Error clearing knowledge base: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("status")
def knowledge_status():
    """Show embedder, vector DB path, and document count."""
    settings = _get_settings()

    console.print()
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

    # Try to get vector count
    try:
        from vandelay.knowledge.embedder import create_embedder

        embedder = create_embedder(settings)
        if embedder:
            from agno.vectordb.lancedb import LanceDb

            vdb = LanceDb(
                uri=str(db_path),
                table_name="vandelay_knowledge",
                embedder=embedder,
            )
            if hasattr(vdb, "table") and vdb.table is not None:
                count = vdb.table.count_rows()
            elif hasattr(vdb, "_table") and vdb._table is not None:
                count = vdb._table.count_rows()
            else:
                count = 0
            console.print(f"  [bold]Vectors:[/bold]    {count}")
        else:
            console.print("  [bold]Vectors:[/bold]    [yellow]embedder unavailable[/yellow]")
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
    """Re-index the built-in Agno documentation corpus."""
    import asyncio

    knowledge, _vector_db = _ensure_knowledge()

    from vandelay.knowledge.corpus import corpus_needs_refresh, index_corpus

    if not force and not corpus_needs_refresh():
        console.print("[dim]Corpus is already up to date.[/dim]")
        raise typer.Exit()

    console.print("[bold]Indexing Agno documentation corpus...[/bold]")
    count = asyncio.run(index_corpus(knowledge, force=force))
    console.print(f"\n  [green]✓[/green] Indexed {count} URL(s).")
