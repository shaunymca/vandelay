"""Config tab — section-based settings editor."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    Switch,
    TextArea,
)

from vandelay.config.constants import COMMON_TIMEZONES as _TIMEZONES

_SECTIONS: list[tuple[str, str]] = [
    ("general",   "General"),
    ("server",    "Server"),
    ("knowledge", "Knowledge"),
    ("tools",     "Tools"),
    ("safety",    "Safety"),
    ("heartbeat", "Heartbeat"),
    ("channels",  "Channels"),
    ("deep_work", "Deep Work"),
]

_SAFETY_MODES = [("confirm", "confirm"), ("trust", "trust"), ("tiered", "tiered")]
_DW_ACTIVATION = [("suggest", "suggest"), ("explicit", "explicit"), ("auto", "auto")]
_EMBEDDER_PROVIDERS = [
    ("", "auto (match model provider)"),
    ("openai", "openai"),
    ("google", "google"),
    ("ollama", "ollama"),
]
_EMBEDDER_MODELS: dict[str, list[str]] = {
    "openai": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
    "google": ["text-embedding-004", "text-multilingual-embedding-002"],
    "ollama": [],   # fetched at runtime
}


class ConfigTab(Widget):
    """Two-column config editor: section list | form panel."""

    DEFAULT_CSS = """
    ConfigTab { height: 1fr; }
    ConfigTab > Horizontal { height: 1fr; }

    #cfg-left {
        width: 22;
        border-right: tall #30363d;
        height: 100%;
    }
    #cfg-left-title {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
        text-style: bold;
    }
    #cfg-list { height: 1fr; }
    #cfg-right { width: 1fr; height: 100%; }
    #cfg-empty {
        height: 1fr;
        align: center middle;
        color: #8b949e;
    }

    ConfigTab .save-top {
        height: 3;
        background: #161b22;
        border-bottom: tall #30363d;
        align: left middle;
        padding: 0 2;
    }
    ConfigTab .save-top .panel-title {
        width: 1fr;
        color: #8b949e;
        content-align: left middle;
    }
    ConfigTab .save-top Button { min-width: 10; height: 3; }

    .section-panel { height: 1fr; }
    .cfg-body { height: 1fr; padding: 1 3; }
    ConfigTab .field-label { height: 1; color: #8b949e; margin-top: 1; }
    ConfigTab .field-input { margin-bottom: 1; }
    ConfigTab .hint { color: #8b949e; text-style: italic; }
    ConfigTab .hint-wrap { color: #8b949e; text-style: italic; height: auto; }

    .channel-heading {
        height: 1;
        color: #c9d1d9;
        text-style: bold;
        margin-top: 2;
    }

    /* tools DataTable */
    #tools-table { height: 1fr; }

    #safety-allowed { height: 8; margin-bottom: 1; }
    #safety-blocked { height: 8; margin-bottom: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._enabled_tools: set[str] = set()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _settings(self):  # noqa: ANN202
        from vandelay.config.settings import get_settings
        return get_settings()

    def _all_tool_data(self) -> list[tuple[str, dict]]:
        """Return (name, metadata) for every registered tool, sorted by name."""
        import json
        try:
            from vandelay.config.constants import VANDELAY_HOME
            f = VANDELAY_HOME / "tool_registry.json"
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8"))
                tools = data.get("tools", data)
                if isinstance(tools, dict):
                    return sorted(tools.items())
                if isinstance(tools, list):
                    return sorted(
                        (t.get("name", t), t) if isinstance(t, dict) else (t, {})
                        for t in tools
                    )
        except Exception:
            pass
        return [(t, {}) for t in sorted([
            "shell", "file", "python", "duckduckgo", "camoufox",
            "gmail", "calendar", "drive", "sheets", "notion",
            "github", "slack", "discord", "docker",
        ])]

    # ── Compose ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:  # noqa: PLR0915
        with Horizontal():
            with Vertical(id="cfg-left"):
                yield Static("Config", id="cfg-left-title")
                yield ListView(id="cfg-list")

            with Vertical(id="cfg-right"):
                yield Static("Select a section", id="cfg-empty")

                # ── General ──────────────────────────────────────────────
                with Vertical(id="panel-general", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("General", classes="panel-title")
                        yield Button("Save", id="save-general", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Label("User ID", classes="field-label")
                        yield Input(
                            id="general-user-id", classes="field-input",
                            placeholder="your@email.com or any identifier",
                        )
                        yield Label("Timezone", classes="field-label")
                        yield Select(
                            _TIMEZONES, id="general-timezone", allow_blank=False,
                        )

                # ── Server ───────────────────────────────────────────────
                with Vertical(id="panel-server", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Server", classes="panel-title")
                        yield Button("Save", id="save-server", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Label("Host", classes="field-label")
                        yield Input(
                            id="server-host", classes="field-input",
                            placeholder="0.0.0.0",
                        )
                        yield Label("Port", classes="field-label")
                        yield Input(
                            id="server-port", classes="field-input",
                            placeholder="8000",
                        )
                        yield Label("Secret Key", classes="field-label")
                        yield Input(
                            id="server-secret-key", classes="field-input",
                            password=True, placeholder="leave blank to keep existing",
                        )
                        yield Label(
                            "[dim]Restart required to apply server changes.[/dim]",
                            classes="hint",
                        )

                # ── Knowledge ────────────────────────────────────────────
                with Vertical(id="panel-knowledge", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Knowledge", classes="panel-title")
                        yield Button("Save", id="save-knowledge", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Label("Enabled", classes="field-label")
                        yield Switch(id="knowledge-enabled")
                        yield Label("Embedder Provider", classes="field-label")
                        yield Select(
                            _EMBEDDER_PROVIDERS, id="embedder-provider", allow_blank=False,
                        )
                        yield Label("Embedder Model", classes="field-label")
                        # Select shown for known providers; Input shown for ollama/auto
                        yield Select([], id="embedder-model-select", allow_blank=True)
                        yield Input(
                            id="embedder-model-input", classes="field-input",
                            placeholder="e.g. llama3.2 or text-embedding-3-small",
                        )
                        yield Label("Embedder API Key", classes="field-label")
                        yield Input(
                            id="embedder-api-key", classes="field-input",
                            password=True,
                            placeholder="optional — leave blank to reuse model key",
                        )
                        yield Label("Base URL", classes="field-label")
                        yield Input(
                            id="embedder-base-url", classes="field-input",
                            placeholder="optional custom endpoint",
                        )

                # ── Tools ─────────────────────────────────────────────────
                with Vertical(id="panel-tools", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Tools", classes="panel-title")
                        yield Button("Save", id="save-tools", variant="primary")
                    yield DataTable(id="tools-table", cursor_type="row", show_header=True)

                # ── Safety ───────────────────────────────────────────────
                with Vertical(id="panel-safety", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Safety", classes="panel-title")
                        yield Button("Save", id="save-safety", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Label("Mode", classes="field-label")
                        yield Select(_SAFETY_MODES, id="safety-mode", allow_blank=False)
                        yield Label("Command Timeout (seconds)", classes="field-label")
                        yield Input(
                            id="safety-timeout", classes="field-input",
                            placeholder="120",
                        )
                        yield Label("Allowed Commands (one per line)", classes="field-label")
                        yield TextArea("", id="safety-allowed")
                        yield Label("Blocked Patterns (one per line)", classes="field-label")
                        yield TextArea("", id="safety-blocked")

                # ── Heartbeat ────────────────────────────────────────────
                with Vertical(id="panel-heartbeat", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Heartbeat", classes="panel-title")
                        yield Button("Save", id="save-heartbeat", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Label("Enabled", classes="field-label")
                        yield Switch(id="heartbeat-enabled")
                        yield Label("Interval (minutes)", classes="field-label")
                        yield Input(
                            id="heartbeat-interval", classes="field-input",
                            placeholder="30",
                        )
                        yield Label("Active From Hour (0–23)", classes="field-label")
                        yield Input(
                            id="heartbeat-start", classes="field-input",
                            placeholder="8",
                        )
                        yield Label("Active Until Hour (0–23)", classes="field-label")
                        yield Input(
                            id="heartbeat-end", classes="field-input",
                            placeholder="22",
                        )
                        yield Label("Timezone", classes="field-label")
                        yield Select(
                            _TIMEZONES, id="heartbeat-timezone", allow_blank=False,
                        )

                # ── Channels ─────────────────────────────────────────────
                with Vertical(id="panel-channels", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Channels", classes="panel-title")
                        yield Button("Save", id="save-channels", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Static("Telegram", classes="channel-heading")
                        yield Label("Enabled", classes="field-label")
                        yield Switch(id="telegram-enabled")
                        yield Label("Bot Token", classes="field-label")
                        yield Input(
                            id="telegram-token", classes="field-input",
                            password=True, placeholder="from @BotFather",
                        )
                        yield Label("Chat ID", classes="field-label")
                        yield Input(
                            id="telegram-chat-id", classes="field-input",
                            placeholder="your Telegram user/chat ID",
                        )
                        yield Label(
                            "[dim]To find your Chat ID: enter your token above, then open "
                            "https://api.telegram.org/bot<TOKEN>/getUpdates in a browser "
                            "and look for chat.id in the response.[/dim]",
                            id="telegram-chat-id-hint",
                            classes="hint-wrap",
                        )
                        yield Static("WhatsApp", classes="channel-heading")
                        yield Label("Enabled", classes="field-label")
                        yield Switch(id="whatsapp-enabled")
                        yield Label("Access Token", classes="field-label")
                        yield Input(
                            id="whatsapp-token", classes="field-input",
                            password=True, placeholder="Meta access token",
                        )
                        yield Label("Phone Number ID", classes="field-label")
                        yield Input(id="whatsapp-phone", classes="field-input")
                        yield Label("Verify Token", classes="field-label")
                        yield Input(id="whatsapp-verify", classes="field-input", password=True)
                        yield Label("App Secret", classes="field-label")
                        yield Input(id="whatsapp-secret", classes="field-input", password=True)

                # ── Deep Work ────────────────────────────────────────────
                with Vertical(id="panel-deep-work", classes="section-panel"):
                    with Horizontal(classes="save-top"):
                        yield Static("Deep Work", classes="panel-title")
                        yield Button("Save", id="save-deep-work", variant="primary")
                    with ScrollableContainer(classes="cfg-body"):
                        yield Label("Enabled", classes="field-label")
                        yield Switch(id="deep-work-enabled")
                        yield Label("Activation", classes="field-label")
                        yield Select(
                            _DW_ACTIVATION, id="deep-work-activation", allow_blank=False,
                        )
                        yield Label("Max Iterations", classes="field-label")
                        yield Input(
                            id="deep-work-max-iter", classes="field-input",
                            placeholder="50",
                        )
                        yield Label("Max Time (minutes)", classes="field-label")
                        yield Input(
                            id="deep-work-max-time", classes="field-input",
                            placeholder="240",
                        )
                        yield Label("Progress Interval (minutes)", classes="field-label")
                        yield Input(
                            id="deep-work-progress-interval", classes="field-input",
                            placeholder="5",
                        )
                        yield Label("Progress Channel", classes="field-label")
                        yield Input(
                            id="deep-work-progress-channel", classes="field-input",
                            placeholder="leave blank for originating channel",
                        )
                        yield Label("Save results to workspace", classes="field-label")
                        yield Switch(id="deep-work-save-ws")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._hide_all()
        self._populate_list()
        # Set initial embedder model widget visibility
        self._update_embedder_model_options("", "")

    def on_show(self) -> None:
        self._populate_list()

    # ── Navigation ────────────────────────────────────────────────────────

    def _populate_list(self) -> None:
        lv = self.query_one("#cfg-list", ListView)
        lv.clear()
        for _, label in _SECTIONS:
            lv.append(ListItem(Label(label)))

    def _hide_all(self) -> None:
        self.query_one("#cfg-empty").display = True
        for key, _ in _SECTIONS:
            self.query_one(f"#panel-{key.replace('_', '-')}").display = False

    def _show_panel(self, key: str) -> None:
        self.query_one("#cfg-empty").display = False
        for k, _ in _SECTIONS:
            self.query_one(f"#panel-{k.replace('_', '-')}").display = (k == key)
        self._load_section(key)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "cfg-list":
            return
        idx = event.list_view.index
        if idx is None or idx >= len(_SECTIONS):
            return
        key, _ = _SECTIONS[idx]
        self._show_panel(key)

    # ── Loading ───────────────────────────────────────────────────────────

    def _load_section(self, key: str) -> None:
        import contextlib
        try:
            s = self._settings()
        except Exception:
            return

        if key == "general":
            self.query_one("#general-user-id", Input).value = s.user_id or ""
            with contextlib.suppress(Exception):
                self.query_one("#general-timezone", Select).value = s.timezone or "UTC"

        elif key == "server":
            self.query_one("#server-host", Input).value = s.server.host or ""
            self.query_one("#server-port", Input).value = str(s.server.port)

        elif key == "knowledge":
            self.query_one("#knowledge-enabled", Switch).value = s.knowledge.enabled
            provider = s.knowledge.embedder.provider or ""
            model = s.knowledge.embedder.model or ""
            with contextlib.suppress(Exception):
                self.query_one("#embedder-provider", Select).value = provider
            self._update_embedder_model_options(provider, model)
            self.query_one("#embedder-base-url", Input).value = (
                s.knowledge.embedder.base_url or ""
            )

        elif key == "tools":
            self._load_tools_section(s)

        elif key == "safety":
            with contextlib.suppress(Exception):
                self.query_one("#safety-mode", Select).value = s.safety.mode
            self.query_one("#safety-timeout", Input).value = str(
                s.safety.command_timeout_seconds
            )
            self.query_one("#safety-allowed", TextArea).load_text(
                "\n".join(s.safety.allowed_commands)
            )
            self.query_one("#safety-blocked", TextArea).load_text(
                "\n".join(s.safety.blocked_patterns)
            )

        elif key == "heartbeat":
            self.query_one("#heartbeat-enabled", Switch).value = s.heartbeat.enabled
            self.query_one("#heartbeat-interval", Input).value = str(
                s.heartbeat.interval_minutes
            )
            self.query_one("#heartbeat-start", Input).value = str(
                s.heartbeat.active_hours_start
            )
            self.query_one("#heartbeat-end", Input).value = str(s.heartbeat.active_hours_end)
            with contextlib.suppress(Exception):
                self.query_one("#heartbeat-timezone", Select).value = (
                    s.heartbeat.timezone or "UTC"
                )

        elif key == "channels":
            self.query_one("#telegram-enabled", Switch).value = s.channels.telegram_enabled
            token = s.channels.telegram_bot_token or ""
            if token:
                self.query_one("#telegram-token", Input).value = token
            self.query_one("#telegram-chat-id", Input).value = (
                s.channels.telegram_chat_id or ""
            )
            # Update hint with real URL if token is known
            if token:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                hint = (
                    f"[dim]To find your Chat ID: message your bot, then open "
                    f"{url} in a browser and look for chat.id in the response.[/dim]"
                )
            else:
                hint = (
                    "[dim]To find your Chat ID: enter your token above, then open "
                    "https://api.telegram.org/bot<TOKEN>/getUpdates in a browser "
                    "and look for chat.id in the response.[/dim]"
                )
            self.query_one("#telegram-chat-id-hint", Label).update(hint)
            self.query_one("#whatsapp-enabled", Switch).value = s.channels.whatsapp_enabled
            if s.channels.whatsapp_access_token:
                self.query_one("#whatsapp-token", Input).value = (
                    s.channels.whatsapp_access_token
                )
            self.query_one("#whatsapp-phone", Input).value = (
                s.channels.whatsapp_phone_number_id or ""
            )
            if s.channels.whatsapp_verify_token:
                self.query_one("#whatsapp-verify", Input).value = (
                    s.channels.whatsapp_verify_token
                )
            if s.channels.whatsapp_app_secret:
                self.query_one("#whatsapp-secret", Input).value = s.channels.whatsapp_app_secret

        elif key == "deep_work":
            self.query_one("#deep-work-enabled", Switch).value = s.deep_work.enabled
            with contextlib.suppress(Exception):
                self.query_one("#deep-work-activation", Select).value = s.deep_work.activation
            self.query_one("#deep-work-max-iter", Input).value = str(s.deep_work.max_iterations)
            self.query_one("#deep-work-max-time", Input).value = str(
                s.deep_work.max_time_minutes
            )
            self.query_one("#deep-work-progress-interval", Input).value = str(
                s.deep_work.progress_interval_minutes
            )
            self.query_one("#deep-work-progress-channel", Input).value = (
                s.deep_work.progress_channel or ""
            )
            self.query_one("#deep-work-save-ws", Switch).value = (
                s.deep_work.save_results_to_workspace
            )

    def _load_tools_section(self, s) -> None:  # noqa: ANN001
        self._enabled_tools = set(s.enabled_tools)
        table = self.query_one("#tools-table", DataTable)
        if not table.columns:
            table.add_column("", key="dot", width=3)
            table.add_column("Tool", key="name", width=22)
            table.add_column("Category", key="category")
        table.clear(columns=False)
        for name, meta in self._all_tool_data():
            dot = "[green]●[/green]" if name in self._enabled_tools else "[dim]○[/dim]"
            category = meta.get("category", "") if isinstance(meta, dict) else ""
            table.add_row(dot, name, category, key=name)

    # ── Embedder model dropdown ───────────────────────────────────────────

    def _update_embedder_model_options(self, provider: str, current: str = "") -> None:
        models = _EMBEDDER_MODELS.get(provider, [])
        use_select = bool(models)

        msel = self.query_one("#embedder-model-select", Select)
        minput = self.query_one("#embedder-model-input", Input)

        if use_select:
            msel.set_options([(m, m) for m in models])
            import contextlib
            with contextlib.suppress(Exception):
                if current in models:
                    msel.value = current
            msel.display = True
            minput.display = False
        else:
            msel.display = False
            minput.display = True
            minput.value = current
            if provider == "ollama":
                self.run_worker(self._fetch_ollama_embedder_models)

    async def _fetch_ollama_embedder_models(self) -> None:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            if models:
                self.app.notify(
                    f"Ollama: {len(models)} model(s) available. Type a name above.",
                    severity="information", timeout=3,
                )
        except Exception:
            pass

    # ── Event handlers ────────────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "telegram-token":
            token = event.value.strip()
            if token:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                hint = (
                    f"[dim]To find your Chat ID: message your bot, then open "
                    f"{url} in a browser and look for chat.id in the response.[/dim]"
                )
            else:
                hint = (
                    "[dim]To find your Chat ID: enter your token above, then open "
                    "https://api.telegram.org/bot<TOKEN>/getUpdates in a browser "
                    "and look for chat.id in the response.[/dim]"
                )
            import contextlib
            with contextlib.suppress(Exception):
                self.query_one("#telegram-chat-id-hint", Label).update(hint)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "embedder-provider":
            provider = str(event.value) if event.value is not None else ""
            self._update_embedder_model_options(provider)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "tools-table":
            return
        tool = str(event.row_key.value)
        table = self.query_one("#tools-table", DataTable)
        if tool in self._enabled_tools:
            self._enabled_tools.discard(tool)
            table.update_cell(event.row_key, "dot", "[dim]○[/dim]")
        else:
            self._enabled_tools.add(tool)
            table.update_cell(event.row_key, "dot", "[green]●[/green]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("save-"):
            key = bid[5:].replace("-", "_")
            self._save_section(key)

    # ── Saving ────────────────────────────────────────────────────────────

    def _save_section(self, key: str) -> None:
        try:
            from vandelay.config.settings import get_settings
            s = get_settings()
            getattr(self, f"_save_{key}")(s)
            s.save()
            get_settings.cache_clear()
            label = dict(_SECTIONS).get(key, key)
            self.app.notify(f"{label} saved.", severity="information", timeout=3)
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    def _save_general(self, s) -> None:  # noqa: ANN001
        s.user_id = self.query_one("#general-user-id", Input).value.strip()
        tz_val = self.query_one("#general-timezone", Select).value
        s.timezone = str(tz_val) if tz_val else "UTC"

    def _save_server(self, s) -> None:  # noqa: ANN001
        s.server.host = self.query_one("#server-host", Input).value.strip() or "0.0.0.0"
        port_str = self.query_one("#server-port", Input).value.strip()
        if port_str.isdigit():
            s.server.port = int(port_str)
        secret = self.query_one("#server-secret-key", Input).value.strip()
        if secret:
            from vandelay.config.env_utils import write_env_key
            write_env_key("VANDELAY_SECRET_KEY", secret)

    def _save_knowledge(self, s) -> None:  # noqa: ANN001
        s.knowledge.enabled = self.query_one("#knowledge-enabled", Switch).value
        provider_val = self.query_one("#embedder-provider", Select).value
        s.knowledge.embedder.provider = str(provider_val) if provider_val else ""
        # Read model from whichever widget is visible
        msel = self.query_one("#embedder-model-select", Select)
        minput = self.query_one("#embedder-model-input", Input)
        if msel.display and msel.value:
            s.knowledge.embedder.model = str(msel.value)
        else:
            s.knowledge.embedder.model = minput.value.strip()
        s.knowledge.embedder.base_url = (
            self.query_one("#embedder-base-url", Input).value.strip()
        )
        api_key = self.query_one("#embedder-api-key", Input).value.strip()
        if api_key:
            from vandelay.config.env_utils import write_env_key
            write_env_key("VANDELAY_EMBEDDER_API_KEY", api_key)

    def _save_tools(self, s) -> None:  # noqa: ANN001
        s.enabled_tools = sorted(self._enabled_tools)

    def _save_safety(self, s) -> None:  # noqa: ANN001
        mode_val = self.query_one("#safety-mode", Select).value
        if mode_val:
            s.safety.mode = str(mode_val)
        timeout_str = self.query_one("#safety-timeout", Input).value.strip()
        if timeout_str.isdigit():
            s.safety.command_timeout_seconds = int(timeout_str)
        s.safety.allowed_commands = [
            ln.strip()
            for ln in self.query_one("#safety-allowed", TextArea).text.splitlines()
            if ln.strip()
        ]
        s.safety.blocked_patterns = [
            ln.strip()
            for ln in self.query_one("#safety-blocked", TextArea).text.splitlines()
            if ln.strip()
        ]

    def _save_heartbeat(self, s) -> None:  # noqa: ANN001
        s.heartbeat.enabled = self.query_one("#heartbeat-enabled", Switch).value
        interval = self.query_one("#heartbeat-interval", Input).value.strip()
        if interval.isdigit():
            s.heartbeat.interval_minutes = int(interval)
        start = self.query_one("#heartbeat-start", Input).value.strip()
        if start.isdigit():
            s.heartbeat.active_hours_start = int(start)
        end = self.query_one("#heartbeat-end", Input).value.strip()
        if end.isdigit():
            s.heartbeat.active_hours_end = int(end)
        tz_val = self.query_one("#heartbeat-timezone", Select).value
        if tz_val:
            s.heartbeat.timezone = str(tz_val)

    def _save_channels(self, s) -> None:  # noqa: ANN001
        from vandelay.config.env_utils import write_env_key
        s.channels.telegram_enabled = self.query_one("#telegram-enabled", Switch).value
        token = self.query_one("#telegram-token", Input).value.strip()
        if token:
            write_env_key("TELEGRAM_TOKEN", token)
        s.channels.telegram_chat_id = (
            self.query_one("#telegram-chat-id", Input).value.strip()
        )
        s.channels.whatsapp_enabled = self.query_one("#whatsapp-enabled", Switch).value
        wa_token = self.query_one("#whatsapp-token", Input).value.strip()
        if wa_token:
            write_env_key("WHATSAPP_ACCESS_TOKEN", wa_token)
        s.channels.whatsapp_phone_number_id = (
            self.query_one("#whatsapp-phone", Input).value.strip()
        )
        verify = self.query_one("#whatsapp-verify", Input).value.strip()
        if verify:
            write_env_key("WHATSAPP_VERIFY_TOKEN", verify)
        secret = self.query_one("#whatsapp-secret", Input).value.strip()
        if secret:
            write_env_key("WHATSAPP_APP_SECRET", secret)

    def _save_deep_work(self, s) -> None:  # noqa: ANN001
        s.deep_work.enabled = self.query_one("#deep-work-enabled", Switch).value
        act_val = self.query_one("#deep-work-activation", Select).value
        if act_val:
            s.deep_work.activation = str(act_val)
        max_iter = self.query_one("#deep-work-max-iter", Input).value.strip()
        if max_iter.isdigit():
            s.deep_work.max_iterations = int(max_iter)
        max_time = self.query_one("#deep-work-max-time", Input).value.strip()
        if max_time.isdigit():
            s.deep_work.max_time_minutes = int(max_time)
        prog = self.query_one("#deep-work-progress-interval", Input).value.strip()
        if prog.isdigit():
            s.deep_work.progress_interval_minutes = int(prog)
        s.deep_work.progress_channel = (
            self.query_one("#deep-work-progress-channel", Input).value.strip()
        )
        s.deep_work.save_results_to_workspace = (
            self.query_one("#deep-work-save-ws", Switch).value
        )
