"""Agents tab — team members list and prompt file editor."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Static, TextArea


class AgentsTab(Widget):
    """Team member manager — list members, view and edit their .md prompt files."""

    DEFAULT_CSS = """
    AgentsTab {
        height: 1fr;
    }
    AgentsTab > Horizontal {
        height: 1fr;
    }
    #agents-left {
        width: 28;
        border-right: tall #30363d;
        height: 100%;
    }
    #agents-left-title {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
        text-style: bold;
    }
    #agents-list {
        height: 1fr;
    }
    #agents-right {
        width: 1fr;
        height: 100%;
    }
    #agents-editor {
        height: 1fr;
    }
    #agents-actions {
        height: 3;
        background: #161b22;
        border-top: tall #30363d;
        align: right middle;
        padding: 0 2;
    }
    #agents-name {
        width: 1fr;
        height: 1;
        color: #8b949e;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_path: Path | None = None
        self._member_names: list[str] = []

    def _members_dir(self) -> Path:
        try:
            from vandelay.config.constants import MEMBERS_DIR
            return MEMBERS_DIR
        except Exception:
            return Path.home() / ".vandelay" / "members"

    def _load_members(self) -> list[tuple[str, bool]]:
        """Return [(name, enabled)] — from settings if available, else from filesystem."""
        try:
            from vandelay.config.settings import Settings, get_settings

            if Settings.config_exists():
                s = get_settings()
                if s.team and s.team.members:
                    return [(m.name, m.enabled) for m in s.team.members]
        except Exception:
            pass
        md = self._members_dir()
        if md.exists():
            return [(p.stem, True) for p in sorted(md.glob("*.md"))]
        return []

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="agents-left"):
                yield Static("Team Members", id="agents-left-title")
                yield ListView(id="agents-list")
            with Vertical(id="agents-right"):
                yield TextArea("", id="agents-editor", language="markdown")
                with Horizontal(id="agents-actions"):
                    yield Static("Select a member to edit their prompt", id="agents-name")
                    yield Button("Save", id="agents-save", variant="primary", disabled=True)

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        lv = self.query_one("#agents-list", ListView)
        lv.clear()
        members = self._load_members()
        self._member_names = []
        if not members:
            lv.append(ListItem(Label("[dim]No team members configured[/dim]")))
            return
        for name, enabled in members:
            dot = "[bold green]●[/bold green]" if enabled else "[bold red]●[/bold red]"
            lv.append(ListItem(Label(f"{dot}  {name}")))
            self._member_names.append(name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is None or idx >= len(self._member_names):
            return
        self._load_member(self._member_names[idx])

    def _load_member(self, name: str) -> None:
        md = self._members_dir()
        path = md / f"{name}.md"
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as exc:
                self.app.notify(f"Could not read {name}.md: {exc}", severity="error")
                return
        else:
            content = f"# {name}\n\n(Prompt file not found — save to create it at {path})\n"
        self._current_path = path
        self.query_one("#agents-editor", TextArea).load_text(content)
        self.query_one("#agents-name", Static).update(f"{name}.md")
        self.query_one("#agents-save", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "agents-save":
            self._save_member()

    def _save_member(self) -> None:
        if not self._current_path:
            return
        try:
            content = self.query_one("#agents-editor", TextArea).text
            self._current_path.parent.mkdir(parents=True, exist_ok=True)
            self._current_path.write_text(content, encoding="utf-8")
            self.app.notify(
                f"Saved {self._current_path.name}", severity="information", timeout=3
            )
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")
