"""Workspace tab — file picker and embedded text editor."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Static, TextArea

_WORKSPACE_FILES = ["SOUL.md", "USER.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md", "BOOTSTRAP.md"]


class WorkspaceTab(Widget):
    """File picker + TextArea editor for workspace and member markdown files."""

    DEFAULT_CSS = """
    WorkspaceTab {
        height: 1fr;
    }
    WorkspaceTab > Horizontal {
        height: 1fr;
    }
    #ws-left {
        width: 26;
        border-right: tall #30363d;
        height: 100%;
    }
    #ws-left-title {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
        text-style: bold;
    }
    #ws-file-list {
        height: 1fr;
    }
    #ws-right {
        width: 1fr;
        height: 100%;
    }
    #ws-editor {
        height: 1fr;
    }
    #ws-actions {
        height: 3;
        background: #161b22;
        border-top: tall #30363d;
        align: right middle;
        padding: 0 2;
    }
    #ws-filename {
        width: 1fr;
        height: 1;
        color: #8b949e;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_path: Path | None = None
        # Map list index → path so we can identify selections without monkey-patching
        self._index_to_path: list[Path] = []

    def _workspace_dir(self) -> Path:
        try:
            from vandelay.config.constants import WORKSPACE_DIR
            return WORKSPACE_DIR
        except Exception:
            return Path.home() / ".vandelay" / "workspace"

    def _members_dir(self) -> Path:
        try:
            from vandelay.config.constants import MEMBERS_DIR
            return MEMBERS_DIR
        except Exception:
            return Path.home() / ".vandelay" / "members"

    def _build_entries(self) -> list[tuple[str, Path]]:
        """Return (display_name, path) pairs for all editable files."""
        ws = self._workspace_dir()
        entries: list[tuple[str, Path]] = []
        for name in _WORKSPACE_FILES:
            p = ws / name
            if p.exists():
                entries.append((name, p))
        md = self._members_dir()
        if md.exists():
            for p in sorted(md.glob("*.md")):
                entries.append((f"members/{p.name}", p))
        return entries

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="ws-left"):
                yield Static("Files", id="ws-left-title")
                yield ListView(id="ws-file-list")
            with Vertical(id="ws-right"):
                yield TextArea("", id="ws-editor", language="markdown")
                with Horizontal(id="ws-actions"):
                    yield Static("Select a file to edit", id="ws-filename")
                    yield Button("Save", id="ws-save", variant="primary", disabled=True)

    def on_mount(self) -> None:
        self._populate_list()

    def on_show(self) -> None:
        """Reload the file list every time this tab becomes visible."""
        self._populate_list()

    def _populate_list(self) -> None:
        lv = self.query_one("#ws-file-list", ListView)
        lv.clear()
        entries = self._build_entries()
        self._index_to_path = []
        for display, path in entries:
            lv.append(ListItem(Label(display)))
            self._index_to_path.append(path)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "ws-file-list":
            return
        idx = event.list_view.index
        if idx is None or idx >= len(self._index_to_path):
            return
        self._load_file(self._index_to_path[idx])

    def _load_file(self, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            self.app.notify(f"Could not read {path.name}: {exc}", severity="error")
            return
        self._current_path = path
        self.query_one("#ws-editor", TextArea).load_text(content)
        self.query_one("#ws-filename", Static).update(str(path))
        self.query_one("#ws-save", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ws-save":
            self._save_file()

    def _save_file(self) -> None:
        if not self._current_path:
            return
        try:
            content = self.query_one("#ws-editor", TextArea).text
            self._current_path.write_text(content, encoding="utf-8")
            self.app.notify(f"Saved {self._current_path.name}", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")
