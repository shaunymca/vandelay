"""Knowledge tab — manage the RAG knowledge base from the TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static, Switch


class KnowledgeTab(Widget):
    """Single-panel knowledge base manager."""

    DEFAULT_CSS = """
    KnowledgeTab { height: 1fr; }

    .save-top {
        height: 3;
        background: #161b22;
        border-bottom: tall #30363d;
        align: left middle;
        padding: 0 2;
    }
    .save-top .panel-title {
        width: 1fr;
        color: #8b949e;
        content-align: left middle;
    }
    .save-top Button { min-width: 10; height: 3; }

    .kb-body { height: 1fr; padding: 1 3; }
    .field-label { height: 1; color: #8b949e; margin-top: 1; margin-bottom: 0; }
    .field-input { margin-bottom: 1; }
    .kb-heading {
        height: 1;
        color: #c9d1d9;
        text-style: bold;
        margin-top: 2;
        margin-bottom: 1;
    }
    .hint { color: #8b949e; text-style: italic; height: 1; }

    #kb-status-box {
        height: auto;
        border: tall #30363d;
        padding: 1 2;
        margin-bottom: 1;
        background: #0d1117;
    }
    .status-row { height: 1; margin-bottom: 0; }
    .status-key { width: 22; color: #8b949e; }
    .status-val { color: #c9d1d9; }

    #kb-result { height: 1; color: #3fb950; margin-top: 1; }
    #kb-add-row { height: 3; margin-bottom: 1; }
    #kb-path-input { width: 1fr; }
    #btn-kb-add { min-width: 14; margin-left: 1; height: 3; }
    #btn-kb-refresh-status { min-width: 18; height: 3; margin-bottom: 1; }
    #btn-kb-refresh-corpus { min-width: 20; height: 3; margin-bottom: 1; }
    #btn-kb-clear { min-width: 18; height: 3; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="save-top"):
                yield Static("Knowledge", classes="panel-title")
                yield Button("Save", id="save-kb-enabled", variant="primary")
            with ScrollableContainer(classes="kb-body"):
                yield Label("Enabled", classes="field-label")
                yield Switch(id="kb-enabled")
                yield Label(
                    "[dim]Requires a compatible embedder (OpenAI, Google, or Ollama).[/dim]",
                    classes="hint",
                )

                yield Static("Status", classes="kb-heading")
                yield Button("Refresh Status", id="btn-kb-refresh-status", variant="default")
                with Vertical(id="kb-status-box"):
                    with Horizontal(classes="status-row"):
                        yield Static("Embedder", classes="status-key")
                        yield Static("—", id="kb-stat-embedder", classes="status-val")
                    with Horizontal(classes="status-row"):
                        yield Static("Vector DB path", classes="status-key")
                        yield Static("—", id="kb-stat-path", classes="status-val")
                    with Horizontal(classes="status-row"):
                        yield Static("Vectors (shared)", classes="status-key")
                        yield Static("—", id="kb-stat-count", classes="status-val")

                yield Static("Add Document", classes="kb-heading")
                yield Label("File or directory path", classes="field-label")
                with Horizontal(id="kb-add-row"):
                    yield Input(
                        placeholder="e.g. /path/to/doc.pdf or ~/notes/",
                        id="kb-path-input",
                        classes="field-input",
                    )
                    yield Button("Add", id="btn-kb-add", variant="success")

                yield Static("Corpus", classes="kb-heading")
                yield Label(
                    "[dim]Re-index the built-in Agno + Vandelay documentation.[/dim]",
                    classes="hint",
                )
                yield Button("Refresh Corpus", id="btn-kb-refresh-corpus", variant="default")

                yield Static("Danger Zone", classes="kb-heading")
                yield Label(
                    "[dim]Remove all vectors from the shared knowledge base.[/dim]",
                    classes="hint",
                )
                yield Button("Clear Knowledge Base", id="btn-kb-clear", variant="error")

                yield Static("", id="kb-result")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._load()

    def on_show(self) -> None:
        self._load()

    def _load(self) -> None:
        import contextlib
        with contextlib.suppress(Exception):
            from vandelay.config.settings import get_settings
            s = get_settings()
            self.query_one("#kb-enabled", Switch).value = s.knowledge.enabled
        self._refresh_status()

    # ── Status refresh ────────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        import contextlib
        with contextlib.suppress(Exception):
            from vandelay.config.constants import VANDELAY_HOME
            from vandelay.config.settings import get_settings
            from vandelay.knowledge.vectordb import get_vector_count, is_knowledge_supported

            s = get_settings()
            ecfg = s.knowledge.embedder
            provider = ecfg.provider or s.model.provider
            self.query_one("#kb-stat-embedder", Static).update(provider or "—")

            db_path = VANDELAY_HOME / "data" / "knowledge_vectors"
            self.query_one("#kb-stat-path", Static).update(str(db_path))

            if not is_knowledge_supported() or not s.knowledge.enabled:
                self.query_one("#kb-stat-count", Static).update(
                    "[dim]unavailable[/dim]" if not is_knowledge_supported() else "[dim]disabled[/dim]"
                )
                return

            from vandelay.knowledge.setup import create_knowledge
            k = create_knowledge(s)
            if k:
                count = get_vector_count(k.vector_db)
                self.query_one("#kb-stat-count", Static).update(str(count))
            else:
                self.query_one("#kb-stat-count", Static).update("[dim]unavailable[/dim]")

    # ── Button handlers ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "save-kb-enabled":
            self._save_enabled()
        elif bid == "btn-kb-refresh-status":
            self._refresh_status()
            self.query_one("#kb-result", Static).update("[green]Status refreshed.[/green]")
        elif bid == "btn-kb-add":
            self.run_worker(self._do_add(), exclusive=True)
        elif bid == "btn-kb-refresh-corpus":
            self.run_worker(self._do_refresh_corpus(), exclusive=True)
        elif bid == "btn-kb-clear":
            self.run_worker(self._do_clear(), exclusive=True)

    def _save_enabled(self) -> None:
        try:
            from vandelay.config.settings import get_settings
            s = get_settings()
            s.knowledge.enabled = self.query_one("#kb-enabled", Switch).value
            s.save()
            get_settings.cache_clear()
            self.app.notify("Knowledge settings saved.", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    async def _do_add(self) -> None:
        import asyncio
        from pathlib import Path
        path_str = self.query_one("#kb-path-input", Input).value.strip()
        if not path_str:
            self.query_one("#kb-result", Static).update("[red]Enter a file or directory path.[/red]")
            return
        target = Path(path_str).expanduser().resolve()
        if not target.exists():
            self.query_one("#kb-result", Static).update(f"[red]Path not found: {target}[/red]")
            return
        self.query_one("#kb-result", Static).update("[dim]Adding…[/dim]")
        try:
            loop = asyncio.get_event_loop()

            def _add() -> str:
                from vandelay.cli.knowledge_commands import (
                    SUPPORTED_EXTENSIONS,
                    _find_supported_files,
                    _load_documents,
                    _ensure_knowledge,
                )
                from vandelay.config.settings import get_settings
                s = get_settings()
                if not s.knowledge.enabled:
                    return "Knowledge is disabled — enable it first."
                files = _find_supported_files(target)
                if not files:
                    exts = ", ".join(sorted(SUPPORTED_EXTENSIONS))
                    return f"No supported files found. Supported: {exts}"
                knowledge, _ = _ensure_knowledge()
                added = 0
                for f in files:
                    docs = _load_documents(f)
                    knowledge.load(documents=docs, upsert=True)
                    added += len(docs)
                return f"Added {added} document(s) from {len(files)} file(s)."

            msg = await loop.run_in_executor(None, _add)
            self.query_one("#kb-result", Static).update(f"[green]{msg}[/green]")
            self._refresh_status()
        except Exception as exc:
            self.query_one("#kb-result", Static).update(f"[red]Error: {exc}[/red]")

    async def _do_refresh_corpus(self) -> None:
        import asyncio
        self.query_one("#kb-result", Static).update("[dim]Indexing corpus…[/dim]")
        try:
            loop = asyncio.get_event_loop()

            def _refresh() -> str:
                from vandelay.cli.knowledge_commands import _ensure_knowledge
                from vandelay.knowledge.corpus import index_corpus
                import asyncio as _asyncio
                knowledge, _ = _ensure_knowledge()
                count = _asyncio.run(index_corpus(knowledge, force=True))
                return f"Indexed {count} source(s)."

            msg = await loop.run_in_executor(None, _refresh)
            self.query_one("#kb-result", Static).update(f"[green]{msg}[/green]")
            self._refresh_status()
        except Exception as exc:
            self.query_one("#kb-result", Static).update(f"[red]Error: {exc}[/red]")

    async def _do_clear(self) -> None:
        import asyncio
        self.query_one("#kb-result", Static).update("[dim]Clearing…[/dim]")
        try:
            loop = asyncio.get_event_loop()

            def _clear() -> None:
                from vandelay.cli.knowledge_commands import _ensure_knowledge
                _, vector_db = _ensure_knowledge()
                if hasattr(vector_db, "drop"):
                    vector_db.drop()

            await loop.run_in_executor(None, _clear)
            self.query_one("#kb-result", Static).update("[green]Knowledge base cleared.[/green]")
            self._refresh_status()
        except Exception as exc:
            self.query_one("#kb-result", Static).update(f"[red]Error: {exc}[/red]")
