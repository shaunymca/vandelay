"""Memory tab — view and manage agent DB memories from the TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Static


class MemoryTab(Widget):
    """DataTable of agent memories with delete and clear controls."""

    DEFAULT_CSS = """
    MemoryTab { height: 1fr; }
    MemoryTab > Vertical { height: 1fr; }

    #mem-toolbar {
        height: 3;
        background: #161b22;
        border-bottom: tall #30363d;
        align: left middle;
        padding: 0 2;
    }
    #mem-toolbar Button { min-width: 16; margin-right: 1; height: 3; }
    #mem-toolbar .spacer { width: 1fr; }

    #mem-table { height: 1fr; }
    #mem-status { height: 1; padding: 0 2; color: #8b949e; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._memories: list = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="mem-toolbar"):
                yield Button("Refresh", id="btn-mem-refresh", variant="default")
                yield Button("Delete Selected", id="btn-mem-delete", variant="warning")
                yield Button("Clear All", id="btn-mem-clear", variant="error")
                yield Static("", classes="spacer")
            yield DataTable(id="mem-table", cursor_type="row", show_header=True)
            yield Static("", id="mem-status")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._setup_table()
        self._load_memories()

    def on_show(self) -> None:
        self._load_memories()

    def _setup_table(self) -> None:
        table = self.query_one("#mem-table", DataTable)
        table.add_column("ID", key="id", width=10)
        table.add_column("Topics", key="topics", width=20)
        table.add_column("Memory", key="memory")
        table.add_column("Created", key="created", width=12)

    # ── Data loading ──────────────────────────────────────────────────────

    def _load_memories(self) -> None:
        from datetime import datetime, timezone
        try:
            from vandelay.config.settings import get_settings
            from vandelay.memory.setup import create_db
            s = get_settings()
            db = create_db(s)
            user_id = s.user_id or "default"
            self._memories = db.get_user_memories(user_id=user_id) or []
        except Exception as exc:
            self._memories = []
            self.query_one("#mem-status", Static).update(f"[red]Load failed: {exc}[/red]")
            return

        table = self.query_one("#mem-table", DataTable)
        table.clear(columns=False)

        for m in self._memories:
            mid = (m.memory_id or "")[:8]
            topics = ", ".join(m.topics or [])
            memory_text = (m.memory or "")[:80].replace("\n", " ")
            if len(m.memory or "") > 80:
                memory_text += "…"
            try:
                ts = datetime.fromtimestamp(m.created_at, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                ts = "—"
            table.add_row(mid, topics, memory_text, ts, key=m.memory_id)

        count = len(self._memories)
        self.query_one("#mem-status", Static).update(
            f"{count} memor{'y' if count == 1 else 'ies'}"
        )

    # ── Button handlers ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "btn-mem-refresh":
            self._load_memories()
        elif bid == "btn-mem-delete":
            self._delete_selected()
        elif bid == "btn-mem-clear":
            self.run_worker(self._do_clear_all(), exclusive=True)

    def _delete_selected(self) -> None:
        table = self.query_one("#mem-table", DataTable)
        row_key = table.cursor_row_key
        if row_key is None:
            self.app.notify("No row selected.", severity="warning", timeout=2)
            return
        memory_id = str(row_key.value) if row_key.value else ""
        if not memory_id:
            return
        try:
            from vandelay.config.settings import get_settings
            from vandelay.memory.setup import create_db
            s = get_settings()
            db = create_db(s)
            user_id = s.user_id or "default"
            db.delete_user_memory(memory_id=memory_id, user_id=user_id)
            self._load_memories()
            self.app.notify("Memory deleted.", severity="information", timeout=2)
        except Exception as exc:
            self.app.notify(f"Delete failed: {exc}", severity="error")

    async def _do_clear_all(self) -> None:
        import asyncio
        try:
            loop = asyncio.get_event_loop()

            def _clear() -> int:
                from vandelay.config.settings import get_settings
                from vandelay.memory.setup import create_db
                s = get_settings()
                db = create_db(s)
                user_id = s.user_id or "default"
                mems = db.get_user_memories(user_id=user_id) or []
                ids = [m.memory_id for m in mems if m.memory_id]
                if ids:
                    db.delete_user_memories(memory_ids=ids, user_id=user_id)
                return len(ids)

            count = await loop.run_in_executor(None, _clear)
            self.app.notify(
                f"Cleared {count} memor{'y' if count == 1 else 'ies'}.",
                severity="information", timeout=3,
            )
            self._load_memories()
        except Exception as exc:
            self.app.notify(f"Clear failed: {exc}", severity="error")
