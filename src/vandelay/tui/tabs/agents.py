"""Agents tab — team members list, sub-nav, and content editor."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static, TextArea

# Workspace prompt files in the order they appear in the system prompt.
_LEADER_PROMPT_FILES = [
    "SOUL.md",
    "USER.md",
    "AGENTS.md",
    "BOOTSTRAP.md",
    "HEARTBEAT.md",
    "TOOLS.md",
]

# Sub-nav entries: (key, label, content_type)
# content_type: "name" | "file" | "model" | "tools"
_LEADER_SUBNAV: list[tuple[str, str, str]] = [
    ("name", "Name", "name"),
    *[(f.lower().replace(".", "_"), f, "file") for f in _LEADER_PROMPT_FILES],
    ("model", "Model", "model"),
    ("tools", "Tools", "tools"),
]

_MEMBER_SUBNAV: list[tuple[str, str, str]] = [
    ("prompt", "Prompt", "file"),
    ("model", "Model", "model"),
    ("tools", "Tools", "tools"),
]


class AgentsTab(Widget):
    """Three-column agent editor: agent list | sub-nav | content."""

    DEFAULT_CSS = """
    AgentsTab {
        height: 1fr;
    }
    AgentsTab > Horizontal {
        height: 1fr;
    }

    /* ── Left column: agent list ──────────────────────── */
    #agents-left {
        width: 22;
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
    #add-agent-btn {
        width: 100%;
        margin: 0;
        border: none;
        height: 3;
    }
    #agents-list {
        height: 1fr;
    }

    /* ── Middle column: sub-nav ───────────────────────── */
    #agents-mid {
        width: 18;
        border-right: tall #30363d;
        height: 100%;
    }
    #agents-mid-title {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
        text-style: bold;
    }
    #subnav-list {
        height: 1fr;
    }
    #subnav-empty {
        height: 1fr;
        align: center middle;
        color: #8b949e;
        padding: 0 1;
    }

    /* ── Right column: content ────────────────────────── */
    #agents-right {
        width: 1fr;
        height: 100%;
    }
    #content-empty {
        height: 1fr;
        align: center middle;
        color: #8b949e;
    }
    #content-file {
        height: 1fr;
    }
    #file-editor {
        height: 1fr;
    }
    #content-name {
        height: 1fr;
        padding: 2 3;
    }
    #content-model {
        height: 1fr;
        padding: 2 3;
    }
    #content-tools {
        height: 1fr;
        padding: 2 3;
    }
    .content-label {
        height: 1;
        color: #8b949e;
        margin-bottom: 1;
    }
    .content-input {
        margin-bottom: 2;
    }
    .content-heading {
        color: #58a6ff;
        text-style: bold;
        height: 1;
        margin-bottom: 2;
    }
    .save-row {
        height: 3;
        background: #161b22;
        border-top: tall #30363d;
        align: right middle;
        padding: 0 2;
    }
    .save-row Button {
        min-width: 10;
    }
    .tool-item {
        height: 1;
        color: #c9d1d9;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        # Selected agent: "leader" or a member slug string
        self._selected_agent: str | None = None
        # Selected sub-nav key
        self._selected_section: str | None = None
        self._selected_content_type: str | None = None
        # For file editing
        self._current_file: Path | None = None
        # Track agent list entries: [(display, agent_id)]
        self._agent_entries: list[tuple[str, str]] = []
        # Sub-nav for current agent: [(key, label, content_type)]
        self._subnav_entries: list[tuple[str, str, str]] = []

    # ── Directory helpers ─────────────────────────────────────────────────

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

    # ── Settings helpers ──────────────────────────────────────────────────

    def _get_settings(self):  # noqa: ANN202
        from vandelay.config.settings import get_settings
        return get_settings()

    def _leader_name(self) -> str:
        try:
            return self._get_settings().agent_name or "Leader"
        except Exception:
            return "Leader"

    def _member_slugs(self) -> list[str]:
        try:
            s = self._get_settings()
            return [m if isinstance(m, str) else m.name for m in s.team.members]
        except Exception:
            return []

    # ── Compose ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal():
            # Left: agent list
            with Vertical(id="agents-left"):
                yield Static("Agents", id="agents-left-title")
                yield Button("+ Add Agent", id="add-agent-btn", variant="default", disabled=True)
                yield ListView(id="agents-list")

            # Middle: sub-nav
            with Vertical(id="agents-mid"):
                yield Static("", id="agents-mid-title")
                yield Static(
                    "Select an agent", id="subnav-empty"
                )
                yield ListView(id="subnav-list")

            # Right: content panels (only one visible at a time)
            with Vertical(id="agents-right"):
                yield Static(
                    "Select an agent and section", id="content-empty"
                )

                # File editor panel
                with Vertical(id="content-file"):
                    yield TextArea("", id="file-editor", language="markdown")
                    with Horizontal(classes="save-row"):
                        yield Static("", id="file-label", classes="content-label")
                        yield Button("Save", id="file-save", variant="primary")

                # Name editor panel
                with Vertical(id="content-name"):
                    yield Static("Agent Name", classes="content-heading")
                    yield Label("Display name used in responses and the UI.", classes="content-label")  # noqa: E501
                    yield Input(placeholder="Agent name…", id="name-input", classes="content-input")  # noqa: E501
                    with Horizontal(classes="save-row"):
                        yield Button("Save", id="name-save", variant="primary")

                # Model editor panel
                with Vertical(id="content-model"):
                    yield Static("Model", classes="content-heading")
                    yield Label("Provider  (anthropic / openai / google / ollama)", classes="content-label")  # noqa: E501
                    yield Input(placeholder="e.g. anthropic", id="model-provider", classes="content-input")  # noqa: E501
                    yield Label("Model ID", classes="content-label")
                    yield Input(placeholder="e.g. claude-opus-4-6", id="model-id", classes="content-input")  # noqa: E501
                    yield Label(
                        "[dim]Leave blank to inherit the main agent's model.[/dim]",
                        id="model-inherit-note",
                        classes="content-label",
                    )
                    with Horizontal(classes="save-row"):
                        yield Button("Save", id="model-save", variant="primary")

                # Tools panel
                with Vertical(id="content-tools"):
                    yield Static("Tools", classes="content-heading")
                    yield Label("Enabled tools for this agent:", classes="content-label")
                    yield ScrollableContainer(Static("", id="tools-list-body"))
                    yield Label(
                        "[dim]Enable / disable tools in the Config tab.[/dim]",
                        classes="content-label",
                    )

    def on_mount(self) -> None:
        self._hide_all_content()
        self._populate_agent_list()
        self._hide_subnav()

    def on_show(self) -> None:
        self._populate_agent_list()

    # ── Visibility helpers ────────────────────────────────────────────────

    _CONTENT_PANELS = (
        "content-empty", "content-file", "content-name", "content-model", "content-tools"
    )

    def _hide_all_content(self) -> None:
        for wid in self._CONTENT_PANELS:
            self.query_one(f"#{wid}").display = False
        self.query_one("#content-empty").display = True

    def _show_content(self, panel_id: str) -> None:
        for wid in self._CONTENT_PANELS:
            self.query_one(f"#{wid}").display = (wid == panel_id)

    def _hide_subnav(self) -> None:
        self.query_one("#subnav-empty").display = True
        self.query_one("#subnav-list").display = False

    def _show_subnav(self) -> None:
        self.query_one("#subnav-empty").display = False
        self.query_one("#subnav-list").display = True

    # ── Agent list ────────────────────────────────────────────────────────

    def _populate_agent_list(self) -> None:
        lv = self.query_one("#agents-list", ListView)
        lv.clear()
        self._agent_entries = []

        # Leader
        leader = self._leader_name()
        lv.append(ListItem(Label(f"[bold]{leader}[/bold]  [dim](Leader)[/dim]")))
        self._agent_entries.append((leader, "leader"))

        # Members
        for slug in self._member_slugs():
            lv.append(ListItem(Label(f"[green]●[/green]  {slug}")))
            self._agent_entries.append((slug, slug))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "agents-list":
            idx = event.list_view.index
            if idx is None or idx >= len(self._agent_entries):
                return
            _, agent_id = self._agent_entries[idx]
            self._select_agent(agent_id)

        elif event.list_view.id == "subnav-list":
            idx = event.list_view.index
            if idx is None or idx >= len(self._subnav_entries):
                return
            key, _, content_type = self._subnav_entries[idx]
            self._select_section(key, content_type)

    # ── Agent selection ───────────────────────────────────────────────────

    def _select_agent(self, agent_id: str) -> None:
        self._selected_agent = agent_id
        self._selected_section = None
        self._hide_all_content()

        if agent_id == "leader":
            self.query_one("#agents-mid-title", Static).update("Leader")
            self._subnav_entries = _LEADER_SUBNAV
        else:
            self.query_one("#agents-mid-title", Static).update(agent_id)
            self._subnav_entries = _MEMBER_SUBNAV

        lv = self.query_one("#subnav-list", ListView)
        lv.clear()
        for _, label, _ in self._subnav_entries:
            lv.append(ListItem(Label(label)))
        self._show_subnav()

    # ── Section selection ─────────────────────────────────────────────────

    def _select_section(self, key: str, content_type: str) -> None:
        self._selected_section = key
        self._selected_content_type = content_type
        agent = self._selected_agent

        if content_type == "name":
            self._load_name_panel()
        elif content_type == "file":
            self._load_file_panel(key, agent)
        elif content_type == "model":
            self._load_model_panel(agent)
        elif content_type == "tools":
            self._load_tools_panel(agent)

    # ── Name panel ────────────────────────────────────────────────────────

    def _load_name_panel(self) -> None:
        try:
            name = self._get_settings().agent_name
        except Exception:
            name = ""
        self.query_one("#name-input", Input).value = name
        self._show_content("content-name")

    # ── File panel ────────────────────────────────────────────────────────

    def _load_file_panel(self, key: str, agent: str | None) -> None:
        if agent == "leader":
            # key is like "soul_md" → "SOUL.md"
            filename = key.upper().replace("_MD", ".MD").replace("_", ".")
            # Handle special cases
            _map = {k.lower().replace(".", "_"): k for k in _LEADER_PROMPT_FILES}
            filename = _map.get(key, filename)
            path = self._workspace_dir() / filename
        else:
            # Member prompt file
            path = self._members_dir() / f"{agent}.md"

        self._current_file = path
        try:
            content = path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception:
            content = ""

        self.query_one("#file-editor", TextArea).load_text(content)
        self.query_one("#file-label", Static).update(str(path.name))
        self._show_content("content-file")

    # ── Model panel ───────────────────────────────────────────────────────

    def _load_model_panel(self, agent: str | None) -> None:
        try:
            s = self._get_settings()
            if agent == "leader":
                provider = s.model.provider
                model_id = s.model.model_id
            else:
                # Try to find MemberConfig
                member = self._get_member_config(agent or "")
                provider = getattr(member, "model_provider", "") if member else ""
                model_id = getattr(member, "model_id", "") if member else ""
        except Exception:
            provider = ""
            model_id = ""

        self.query_one("#model-provider", Input).value = provider or ""
        self.query_one("#model-id", Input).value = model_id or ""
        # Hide inherit note for leader (their model is canonical)
        self.query_one("#model-inherit-note").display = agent != "leader"
        self._show_content("content-model")

    def _get_member_config(self, slug: str):  # noqa: ANN202
        try:
            from vandelay.config.models import MemberConfig
            s = self._get_settings()
            for m in s.team.members:
                if isinstance(m, MemberConfig) and m.name == slug:
                    return m
        except Exception:
            pass
        return None

    # ── Tools panel ───────────────────────────────────────────────────────

    def _load_tools_panel(self, agent: str | None) -> None:
        try:
            s = self._get_settings()
            if agent == "leader":
                tools = s.enabled_tools
            else:
                member = self._get_member_config(agent or "")
                tools = getattr(member, "tools", s.enabled_tools) if member else s.enabled_tools
        except Exception:
            tools = []

        body = (
            "\n".join(f"[green]●[/green]  {t}" for t in tools)
            if tools else "[dim]No tools enabled[/dim]"
        )
        self.query_one("#tools-list-body", Static).update(body)
        self._show_content("content-tools")

    # ── Button handlers ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "file-save":   self._save_file,
            "name-save":   self._save_name,
            "model-save":  self._save_model,
        }
        handler = handlers.get(event.button.id or "")
        if handler:
            handler()

    def _save_file(self) -> None:
        if not self._current_file:
            return
        try:
            content = self.query_one("#file-editor", TextArea).text
            self._current_file.parent.mkdir(parents=True, exist_ok=True)
            self._current_file.write_text(content, encoding="utf-8")
            self.app.notify(f"Saved {self._current_file.name}", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    def _save_name(self) -> None:
        try:
            name = self.query_one("#name-input", Input).value.strip()
            if not name:
                self.app.notify("Name cannot be empty.", severity="warning")
                return
            s = self._get_settings()
            s.agent_name = name
            s.save()
            self._populate_agent_list()
            self.app.notify(f"Agent name saved: {name}", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    def _save_model(self) -> None:
        try:
            provider = self.query_one("#model-provider", Input).value.strip()
            model_id = self.query_one("#model-id", Input).value.strip()
            s = self._get_settings()

            if self._selected_agent == "leader":
                if provider:
                    s.model.provider = provider
                if model_id:
                    s.model.model_id = model_id
                s.save()
                self.app.notify("Model saved.", severity="information", timeout=3)
            else:
                # Member model — stored in MemberConfig if present, otherwise note limitation
                self.app.notify(
                    "Per-member model override coming soon. "
                    "Edit model in Config tab for now.",
                    severity="warning",
                    timeout=5,
                )
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")
