"""Agents tab — three-column agent editor."""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, Static, TextArea

# Workspace prompt files in system-prompt order.
_LEADER_PROMPT_FILES = [
    "SOUL.md", "USER.md", "AGENTS.md", "BOOTSTRAP.md", "HEARTBEAT.md", "TOOLS.md",
]

_LEADER_SUBNAV: list[tuple[str, str, str]] = [
    ("name", "Name", "name"),
    *[(f.lower().replace(".", "_"), f, "file") for f in _LEADER_PROMPT_FILES],
    ("model", "Model", "model"),
    ("tools", "Tools", "tools"),
]

_MEMBER_SUBNAV: list[tuple[str, str, str]] = [
    ("prompt", "Prompt", "file"),
    ("model",  "Model",  "model"),
    ("tools",  "Tools",  "tools"),
]

# Providers that use a free-text input instead of a Select (too many / dynamic models).
_FREEFORM_PROVIDERS = {"ollama", "openrouter"}


class AgentsTab(Widget):
    """Three-column agent editor: agent list | sub-nav | content."""

    DEFAULT_CSS = """
    AgentsTab { height: 1fr; }
    AgentsTab > Horizontal { height: 1fr; }

    /* ── Left: agent list ─────────────────────────────── */
    #agents-left {
        width: 24;
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
    #agents-list { height: 1fr; }

    /* dot colours — CSS, not Rich markup, so selection highlight can't override */
    Label.dot-on  { color: #3fb950; }
    Label.dot-off { color: #f85149; }

    /* ── Middle: sub-nav ──────────────────────────────── */
    #agents-mid {
        width: 20;
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
    #toggle-btn {
        width: 100%;
        margin: 0;
        border: none;
        height: 3;
    }
    #subnav-list  { height: 1fr; }
    #subnav-empty {
        height: 1fr;
        align: center middle;
        color: #8b949e;
        padding: 0 1;
    }

    /* ── Right: content panels ───────────────────────── */
    #agents-right { width: 1fr; height: 100%; }
    #content-empty {
        height: 1fr;
        align: center middle;
        color: #8b949e;
    }

    /* shared save row at TOP */
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

    /* file panel */
    #content-file { height: 1fr; }
    #file-editor  { height: 1fr; }
    #file-empty-msg {
        height: 1fr;
        align: center middle;
        color: #8b949e;
        padding: 2 4;
    }

    /* name / model panels */
    #content-name, #content-model { height: 1fr; }
    #name-body, #model-body {
        height: 1fr;
        padding: 1 3;
    }
    .field-label {
        height: 1;
        color: #8b949e;
        margin-top: 1;
        margin-bottom: 0;
    }
    .field-input { margin-bottom: 1; }
    .hint { color: #8b949e; height: 1; text-style: italic; }

    /* tools panel */
    #content-tools { height: 1fr; }
    #tools-add-row {
        height: 4;
        background: #161b22;
        border-bottom: tall #30363d;
        padding: 0 2;
        align: left middle;
    }
    #tool-add-select { width: 1fr; }
    #tool-add-btn { min-width: 8; margin-left: 1; }
    #tools-scroll { height: 1fr; }
    .tool-row {
        height: 4;
        border-bottom: solid #21262d;
        padding: 0 2;
        align: left middle;
    }
    .tool-name { width: 1fr; color: #c9d1d9; content-align: left middle; }
    .tool-remove { min-width: 8; margin-right: 1; }
    .tools-empty {
        padding: 2 3;
        color: #8b949e;
        text-style: italic;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._selected_agent: str | None = None   # "leader" or member slug
        self._selected_section: str | None = None
        self._selected_type: str | None = None
        self._current_file: Path | None = None
        self._agent_entries: list[tuple[str, str]] = []
        self._subnav_entries: list[tuple[str, str, str]] = []
        self._save_gen: int = 0   # for auto-save debounce

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

    def _settings(self):  # noqa: ANN202
        from vandelay.config.settings import get_settings
        return get_settings()

    # ── Available tools ───────────────────────────────────────────────────

    def _all_tool_names(self) -> list[str]:
        try:
            from vandelay.config.constants import VANDELAY_HOME
            f = VANDELAY_HOME / "tool_registry.json"
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8"))
                tools = data.get("tools", data)
                if isinstance(tools, dict):
                    return sorted(tools.keys())
                if isinstance(tools, list):
                    return sorted(t.get("name", t) if isinstance(t, dict) else t for t in tools)
        except Exception:
            pass
        return sorted([
            "shell", "file", "python", "duckduckgo", "camoufox",
            "gmail", "calendar", "drive", "sheets", "notion",
            "github", "slack", "discord", "docker",
        ])

    # ── Member helpers ────────────────────────────────────────────────────

    def _enabled_slugs(self) -> list[str]:
        """Slugs currently in settings.team.members (i.e. enabled)."""
        try:
            s = self._settings()
            return [
                m if isinstance(m, str) else m.name
                for m in s.team.members
            ]
        except Exception:
            return []

    def _all_member_slugs(self) -> list[str]:
        """All slugs: enabled + files that exist in members dir."""
        enabled = self._enabled_slugs()
        md = self._members_dir()
        from_files = [p.stem for p in md.glob("*.md")] if md.exists() else []
        seen: set[str] = set()
        result: list[str] = []
        for slug in [*enabled, *from_files]:
            if slug not in seen:
                seen.add(slug)
                result.append(slug)
        return result

    def _is_enabled(self, slug: str) -> bool:
        return slug in self._enabled_slugs()

    def _get_or_create_member_config(self, slug: str):  # noqa: ANN202
        """Return existing MemberConfig for slug, or None if stored as a string."""
        try:
            from vandelay.config.models import MemberConfig
            s = self._settings()
            for m in s.team.members:
                if isinstance(m, MemberConfig) and m.name == slug:
                    return m
        except Exception:
            pass
        return None

    # ── Compose ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:  # noqa: PLR0912
        with Horizontal():
            # ── Left column ──────────────────────────────────────────────
            with Vertical(id="agents-left"):
                yield Static("Agents", id="agents-left-title")
                yield Button("+ Add Agent", id="add-agent-btn", variant="default", disabled=True)
                yield ListView(id="agents-list")

            # ── Middle column ─────────────────────────────────────────────
            with Vertical(id="agents-mid"):
                yield Static("", id="agents-mid-title")
                yield Button("", id="toggle-btn", variant="default")
                yield Static("Select an agent", id="subnav-empty")
                yield ListView(id="subnav-list")

            # ── Right column ──────────────────────────────────────────────
            with Vertical(id="agents-right"):
                yield Static("Select an agent and section", id="content-empty")

                # File panel (auto-saves)
                with Vertical(id="content-file"):
                    yield Static("", id="file-empty-msg")
                    yield TextArea("", id="file-editor", language="markdown")

                # Name panel
                with Vertical(id="content-name"):
                    with Horizontal(classes="save-top"):
                        yield Static("Agent Name", classes="panel-title")
                        yield Button("Save", id="name-save", variant="primary")
                    with Vertical(id="name-body"):
                        yield Label("Display name used in responses and the UI.", classes="field-label")  # noqa: E501
                        yield Input(placeholder="Agent name…", id="name-input", classes="field-input")  # noqa: E501

                # Model panel
                with Vertical(id="content-model"):
                    with Horizontal(classes="save-top"):
                        yield Static("Model", classes="panel-title")
                        yield Button("Save", id="model-save", variant="primary")
                    with Vertical(id="model-body"):
                        yield Label("Provider", classes="field-label")
                        yield Select(
                            [(p, p) for p in [
                                "anthropic", "openai", "google", "ollama", "groq",
                                "deepseek", "mistral", "together", "xai", "openrouter",
                            ]],
                            id="provider-select",
                            allow_blank=False,
                        )
                        yield Label("Model ID", classes="field-label")
                        yield Select([], id="model-select", allow_blank=True)
                        yield Input(
                            placeholder="Model ID (e.g. llama3.2)",
                            id="model-input",
                            classes="field-input",
                        )
                        yield Label(
                            "[dim]Leave blank to inherit the leader's model.[/dim]",
                            id="model-inherit-note",
                            classes="hint",
                        )

                # Tools panel
                with Vertical(id="content-tools"):
                    with Horizontal(id="tools-add-row"):
                        yield Select([], id="tool-add-select", allow_blank=True)
                        yield Button("Add", id="tool-add-btn", variant="success")
                    yield ScrollableContainer(
                        Static("No tools enabled.", id="tools-empty"),
                        id="tools-scroll",
                    )

    def on_mount(self) -> None:
        self._pending_auth_method = "api_key"  # used by on_select_changed
        self._pending_model_id = ""
        self._hide_all()
        self._populate_agent_list()
        self._hide_subnav()
        self.query_one("#toggle-btn").display = False

    def on_show(self) -> None:
        self._populate_agent_list()

    # ── Visibility ────────────────────────────────────────────────────────

    _PANELS = (
        "content-empty", "content-file", "content-name", "content-model", "content-tools"
    )

    def _hide_all(self) -> None:
        for p in self._PANELS:
            self.query_one(f"#{p}").display = False
        self.query_one("#content-empty").display = True

    def _show(self, panel: str) -> None:
        for p in self._PANELS:
            self.query_one(f"#{p}").display = (p == panel)

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

        # Leader first
        try:
            leader = self._settings().agent_name or "Leader"
        except Exception:
            leader = "Leader"
        lbl = Label(f"● {leader}  (Leader)")
        lbl.add_class("dot-on")
        lv.append(ListItem(lbl))
        self._agent_entries.append((leader, "leader"))

        # All members (enabled + disabled)
        enabled = set(self._enabled_slugs())
        for slug in self._all_member_slugs():
            on = slug in enabled
            lbl = Label(f"● {slug}")
            lbl.add_class("dot-on" if on else "dot-off")
            lv.append(ListItem(lbl))
            self._agent_entries.append((slug, slug))

    # ── Agent selection ───────────────────────────────────────────────────

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
            key, _, ctype = self._subnav_entries[idx]
            self._select_section(key, ctype)

    def _select_agent(self, agent_id: str) -> None:
        self._selected_agent = agent_id
        self._selected_section = None
        self._hide_all()

        btn = self.query_one("#toggle-btn", Button)
        if agent_id == "leader":
            self.query_one("#agents-mid-title", Static).update("Leader")
            self._subnav_entries = _LEADER_SUBNAV
            btn.display = False
        else:
            self.query_one("#agents-mid-title", Static).update(agent_id)
            self._subnav_entries = _MEMBER_SUBNAV
            btn.display = True
            self._refresh_toggle_btn(agent_id)

        lv = self.query_one("#subnav-list", ListView)
        lv.clear()
        for _, label, _ in self._subnav_entries:
            lv.append(ListItem(Label(label)))
        self._show_subnav()

    def _refresh_toggle_btn(self, slug: str) -> None:
        enabled = self._is_enabled(slug)
        btn = self.query_one("#toggle-btn", Button)
        if enabled:
            btn.label = "Disable Member"
            btn.variant = "error"
        else:
            btn.label = "Enable Member"
            btn.variant = "success"

    # ── Section selection ─────────────────────────────────────────────────

    def _select_section(self, key: str, ctype: str) -> None:
        self._selected_section = key
        self._selected_type = ctype
        agent = self._selected_agent
        if ctype == "name":
            self._load_name()
        elif ctype == "file":
            self._load_file(key, agent)
        elif ctype == "model":
            self._load_model(agent)
        elif ctype == "tools":
            self._load_tools(agent)

    # ── File panel ────────────────────────────────────────────────────────

    def _load_file(self, key: str, agent: str | None) -> None:
        if agent == "leader":
            _map = {f.lower().replace(".", "_"): f for f in _LEADER_PROMPT_FILES}
            filename = _map.get(key, key)
            path = self._workspace_dir() / filename
        else:
            path = self._members_dir() / f"{agent}.md"

        self._current_file = path
        content = path.read_text(encoding="utf-8") if path.exists() else ""

        editor = self.query_one("#file-editor", TextArea)
        empty_msg = self.query_one("#file-empty-msg", Static)

        if content.strip():
            editor.load_text(content)
            editor.display = True
            empty_msg.display = False
        else:
            editor.display = False
            empty_msg.update(
                "This file is empty.\n\n"
                "Start the server to let the agent populate it,\n"
                "or type here — it will auto-save."
            )
            empty_msg.display = True
            editor.load_text("")  # clear editor so auto-save doesn't write old content

        self._show("content-file")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Auto-save after 1.5 s of inactivity."""
        if not self._current_file:
            return
        self._save_gen += 1
        gen = self._save_gen
        # Show the editor if the user started typing into the empty-file state
        self.query_one("#file-editor", TextArea).display = True
        self.query_one("#file-empty-msg", Static).display = False
        self.set_timer(1.5, lambda: self._autosave(gen))

    def _autosave(self, gen: int) -> None:
        if gen != self._save_gen or not self._current_file:
            return
        try:
            content = self.query_one("#file-editor", TextArea).text
            self._current_file.parent.mkdir(parents=True, exist_ok=True)
            self._current_file.write_text(content, encoding="utf-8")
            self.app.notify(f"Saved {self._current_file.name}", severity="information", timeout=2)
        except Exception as exc:
            self.app.notify(f"Auto-save failed: {exc}", severity="error")

    # ── Name panel ────────────────────────────────────────────────────────

    def _load_name(self) -> None:
        try:
            name = self._settings().agent_name
        except Exception:
            name = ""
        self.query_one("#name-input", Input).value = name or ""
        self._show("content-name")

    # ── Model panel ───────────────────────────────────────────────────────

    def _load_model(self, agent: str | None) -> None:
        try:
            s = self._settings()
            if agent == "leader":
                provider = s.model.provider
                model_id = s.model.model_id
                auth_method = getattr(s.model, "auth_method", "api_key") or "api_key"
            else:
                mc = self._get_or_create_member_config(agent or "")
                provider = getattr(mc, "model_provider", "") or s.model.provider
                model_id = getattr(mc, "model_id", "") or ""
                auth_method = "api_key"
        except Exception:
            provider, model_id, auth_method = "", "", "api_key"

        import contextlib

        # Store pending values so on_select_changed picks them up correctly
        self._pending_auth_method = auth_method
        self._pending_model_id = model_id

        psel = self.query_one("#provider-select", Select)
        with contextlib.suppress(Exception):
            psel.value = provider  # fires on_select_changed asynchronously
        self.query_one("#model-inherit-note").display = agent != "leader"
        self._show("content-model")

    def _update_model_options(self, provider: str, current: str = "", auth_method: str = "api_key") -> None:
        from vandelay.models.catalog import get_codex_model_choices, get_model_choices

        freeform = provider in _FREEFORM_PROVIDERS

        msel = self.query_one("#model-select", Select)
        minput = self.query_one("#model-input", Input)

        if freeform:
            msel.display = False
            minput.display = True
            minput.value = current
            if provider == "ollama":
                self.run_worker(self._fetch_ollama_models)
        else:
            if auth_method == "codex":
                model_options = get_codex_model_choices()
            else:
                model_options = get_model_choices(provider)
            if not model_options:
                # Unknown provider — fall back to freeform
                msel.display = False
                minput.display = True
                minput.value = current
                return
            msel.display = True
            minput.display = False
            opts = [(m.label, m.id) for m in model_options]
            msel.set_options(opts)
            model_ids = [m.id for m in model_options]
            if current in model_ids:
                import contextlib
                with contextlib.suppress(Exception):
                    msel.value = current

    async def _fetch_ollama_models(self) -> None:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            if models:
                self.app.notify(
                    f"Ollama: {len(models)} model(s) found. Type to select.",
                    severity="information", timeout=3,
                )
        except Exception:
            pass  # Ollama not running locally — silently ignore

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "provider-select":
            provider = str(event.value) if event.value is not None else ""
            auth_method = getattr(self, "_pending_auth_method", "api_key")
            model_id = getattr(self, "_pending_model_id", "")
            # Reset pending values so subsequent user-driven changes default to api_key
            self._pending_auth_method = "api_key"
            self._pending_model_id = ""
            self._update_model_options(provider, model_id, auth_method=auth_method)

    # ── Tools panel ───────────────────────────────────────────────────────

    def _current_tools(self, agent: str | None) -> list[str]:
        try:
            s = self._settings()
            if agent == "leader":
                return list(s.enabled_tools)
            mc = self._get_or_create_member_config(agent or "")
            return list(getattr(mc, "tools", s.enabled_tools) if mc else s.enabled_tools)
        except Exception:
            return []

    def _load_tools(self, agent: str | None) -> None:
        self._rebuild_tool_rows(agent)
        self._show("content-tools")

    def _rebuild_tool_rows(self, agent: str | None) -> None:
        """Clear and rebuild the tools scroll area."""
        tools = self._current_tools(agent)
        scroll = self.query_one("#tools-scroll", ScrollableContainer)
        scroll.remove_children()
        if not tools:
            scroll.mount(Static("No tools enabled.", classes="tools-empty"))
        else:
            for t in tools:
                self._mount_tool_row(scroll, t)
        self._refresh_tool_add_select(tools)

    def _mount_tool_row(self, container: ScrollableContainer, tool: str) -> None:
        row = Horizontal(classes="tool-row")

        async def _do() -> None:
            await container.mount(row)
            # Use name= (not id=) so re-mounting after remove_children() never
            # causes DuplicateIds — name is not registered in the global registry.
            await row.mount(Button("Remove", variant="error", classes="tool-remove", name=tool))
            await row.mount(Static(tool, classes="tool-name"))

        self.call_later(_do)

    def _refresh_tool_add_select(self, current: list[str]) -> None:
        all_tools = self._all_tool_names()
        available = [(t, t) for t in all_tools if t not in current]
        sel = self.query_one("#tool-add-select", Select)
        if available:
            sel.set_options(available)
        else:
            sel.set_options([("(all tools enabled)", "")])

    def _save_tools(self, tools: list[str]) -> None:
        agent = self._selected_agent
        try:
            s = self._settings()
            if agent == "leader":
                s.enabled_tools = tools
                s.save()
            else:
                # Upgrade string member to MemberConfig with tool list
                from vandelay.config.models import MemberConfig
                slug = agent or ""
                new_members = []
                found = False
                for m in s.team.members:
                    name = m if isinstance(m, str) else m.name
                    if name == slug:
                        mc = m if isinstance(m, MemberConfig) else MemberConfig(name=slug)
                        mc.tools = tools
                        new_members.append(mc)
                        found = True
                    else:
                        new_members.append(m)
                if not found:
                    new_members.append(MemberConfig(name=slug, tools=tools))
                s.team.members = new_members
                s.save()
        except Exception as exc:
            self.app.notify(f"Failed to save tools: {exc}", severity="error")

    # ── Button handlers ───────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: PLR0912
        bid = event.button.id or ""

        if bid == "name-save":
            self._save_name()
        elif bid == "model-save":
            self._save_model()
        elif bid == "toggle-btn":
            self._toggle_member()
        elif bid == "tool-add-btn":
            self._add_tool()
        elif event.button.has_class("tool-remove"):
            tool = event.button.name or ""
            if tool:
                self._remove_tool(tool)

    def _save_name(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            self.app.notify("Name cannot be empty.", severity="warning")
            return
        try:
            s = self._settings()
            s.agent_name = name
            s.save()
            self._populate_agent_list()
            self.app.notify(f"Name saved: {name}", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    def _save_model(self) -> None:
        agent = self._selected_agent
        try:
            s = self._settings()
            psel = self.query_one("#provider-select", Select)
            provider = str(psel.value) if psel.value is not None else ""

            msel = self.query_one("#model-select", Select)
            minput = self.query_one("#model-input", Input)
            model_id = (
                minput.value.strip()
                if minput.display
                else (str(msel.value) if msel.value else "")
            )

            if agent == "leader":
                if provider:
                    s.model.provider = provider
                if model_id:
                    s.model.model_id = model_id
                s.save()
                self.app.notify("Model saved.", severity="information", timeout=3)
            else:
                self.app.notify(
                    "Per-member model override coming soon.", severity="warning", timeout=4
                )
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    def _toggle_member(self) -> None:
        slug = self._selected_agent
        if not slug or slug == "leader":
            return
        try:
            s = self._settings()
            enabled_list = list(s.team.members)
            slugs = [m if isinstance(m, str) else m.name for m in enabled_list]
            if slug in slugs:
                # Disable: remove from team.members
                s.team.members = [m for m in enabled_list
                                   if (m if isinstance(m, str) else m.name) != slug]
            else:
                # Enable: add back
                s.team.members = [*enabled_list, slug]
            s.save()
            self._populate_agent_list()
            self._refresh_toggle_btn(slug)
            state = "enabled" if slug not in slugs else "disabled"
            self.app.notify(f"{slug} {state}.", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Toggle failed: {exc}", severity="error")

    def _add_tool(self) -> None:
        sel = self.query_one("#tool-add-select", Select)
        tool = str(sel.value) if sel.value else ""
        if not tool:
            return
        agent = self._selected_agent
        tools = self._current_tools(agent)
        if tool in tools:
            return
        tools = [*tools, tool]
        self._save_tools(tools)
        self._rebuild_tool_rows(agent)
        self.app.notify(f"Added tool: {tool}", severity="information", timeout=2)

    def _remove_tool(self, tool: str) -> None:
        agent = self._selected_agent
        tools = [t for t in self._current_tools(agent) if t != tool]
        self._save_tools(tools)
        self._rebuild_tool_rows(agent)
        self.app.notify(f"Removed tool: {tool}", severity="information", timeout=2)
