"""TUI onboarding wizard — 4-step screen: Name → Provider → API Key → Timezone."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, ContentSwitcher, Input, Label, RadioButton, RadioSet, Static


class _HRow(Widget):
    DEFAULT_CSS = "_HRow { layout: horizontal; overflow: hidden hidden; }"

logger = logging.getLogger("vandelay.tui.onboarding")

# Ordered list of (key, display_name) for the provider radio set
_PROVIDER_ORDER = [
    "anthropic",
    "openai",
    "google",
    "ollama",
    "groq",
    "deepseek",
    "mistral",
    "together",
    "xai",
    "openrouter",
]

_DEFAULT_PROVIDER = "anthropic"


class OnboardingScreen(ModalScreen[None]):
    """4-step in-TUI wizard that replaces the post-exit CLI onboarding flow."""

    def __init__(self) -> None:
        super().__init__()
        self._step = 0
        self._agent_name = "Art"
        self._provider = _DEFAULT_PROVIDER
        self._auth_method = "api_key"   # "api_key" | "codex"
        self._api_key = ""
        self._timezone = _detect_tz()

        # Number of real steps — step 2 (API key) may be skipped for Ollama
        self._total_steps = 4  # 0-indexed: 0,1,2,3

    # ------------------------------------------------------------------ #
    # Compose                                                              #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        from vandelay.config.constants import MODEL_PROVIDERS

        with Vertical(id="onboard-container"):
            with _HRow(id="onboard-titlebar"):
                yield Static("  Vandelay Setup", id="onboard-title")
                yield Button("✕", id="btn-close-onboard", variant="default")
            yield Static("", id="onboard-step-label")

            with ContentSwitcher(id="onboard-switcher", initial="step-name"):
                # Step 0 — Agent name
                with Vertical(id="step-name", classes="onboard-step"):
                    yield Label("What should I call your agent?", classes="onboard-q")
                    yield Input(
                        value="Art",
                        placeholder="e.g. Art",
                        id="input-name",
                    )

                # Step 1 — Provider
                with Vertical(id="step-provider", classes="onboard-step"):
                    yield Label("Choose your AI provider:", classes="onboard-q")
                    with RadioSet(id="radio-provider"):
                        for key in _PROVIDER_ORDER:
                            info = MODEL_PROVIDERS.get(key, {})
                            label = info.get("name", key)
                            yield RadioButton(label, value=(key == _DEFAULT_PROVIDER), id=f"rb-{key}")

                # Step 2 — Auth method + API key / Codex
                with Vertical(id="step-key", classes="onboard-step"):
                    # Auth picker — only shown when provider has a subscription option
                    with Vertical(id="auth-choice-section"):
                        yield Label("Authentication method:", classes="onboard-q")
                        with RadioSet(id="radio-auth"):
                            yield RadioButton("", id="rb-auth-codex")
                            yield RadioButton("Use API key", id="rb-auth-apikey")
                    # API key pane
                    with Vertical(id="auth-key-section"):
                        yield Label("", id="key-label", classes="onboard-q")
                        yield Input(password=True, placeholder="Paste your API key…", id="input-key")
                        yield Static("", id="key-hint", classes="onboard-hint")
                    # Codex / subscription pane
                    with Vertical(id="auth-codex-section"):
                        yield Static("", id="codex-status")
                        yield Static("", id="codex-hint", classes="onboard-hint")

                # Step 3 — Timezone
                with Vertical(id="step-tz", classes="onboard-step"):
                    yield Label("Your timezone:", classes="onboard-q")
                    yield Input(
                        value=self._timezone,
                        placeholder="UTC",
                        id="input-tz",
                    )
                    yield Static(
                        "  e.g. America/New_York, Europe/London, UTC",
                        classes="onboard-hint",
                    )

            # Error label
            yield Static("", id="onboard-error")

            # Navigation bar
            with Horizontal(id="onboard-nav"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Next →", id="btn-next", variant="primary")
                yield Button("Finish", id="btn-finish", variant="success")

    def on_mount(self) -> None:
        self._refresh_step()

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-close-onboard":
            self.dismiss(None)
        elif btn == "btn-next":
            self._go_next()
        elif btn == "btn-back":
            self._go_back()
        elif btn == "btn-finish":
            self._finish()

    def _go_next(self) -> None:
        if not self._collect_current():
            return
        self._step = self._next_step(self._step)
        self._refresh_step()

    def _go_back(self) -> None:
        self._step = self._prev_step(self._step)
        self._refresh_step()

    def _next_step(self, step: int) -> int:
        """Return next real step index (skip step 2 for Ollama)."""
        nxt = step + 1
        if nxt == 2 and self._provider == "ollama":
            nxt = 3
        return min(nxt, 3)

    def _prev_step(self, step: int) -> int:
        """Return previous real step index (skip step 2 for Ollama)."""
        prv = step - 1
        if prv == 2 and self._provider == "ollama":
            prv = 1
        return max(prv, 0)

    def _refresh_step(self) -> None:
        """Switch content pane and update nav buttons."""
        pane_ids = ["step-name", "step-provider", "step-key", "step-tz"]
        self.query_one("#onboard-switcher", ContentSwitcher).current = pane_ids[self._step]

        # Step label
        self.query_one("#onboard-step-label", Static).update(
            f"  Step {self._step + 1} of {self._total_steps}"
        )

        # Nav buttons
        is_last = self._step == 3 or (self._step == 2 and self._provider != "ollama" and False)
        real_last = self._step == 3

        self.query_one("#btn-back", Button).display = self._step > 0
        self.query_one("#btn-next", Button).display = not real_last
        self.query_one("#btn-finish", Button).display = real_last

        # Populate dynamic labels for step 2
        if self._step == 2:
            self._update_key_step()

        self.query_one("#onboard-error", Static).update("")

    def _update_key_step(self) -> None:
        from vandelay.config.constants import MODEL_PROVIDERS

        info = MODEL_PROVIDERS.get(self._provider, {})
        token_label = info.get("token_label")
        has_choice = bool(token_label)

        # Show/hide auth picker
        choice_section = self.query_one("#auth-choice-section")
        choice_section.display = has_choice

        if has_choice:
            # Label the subscription radio button dynamically
            self.query_one("#rb-auth-codex", RadioButton).label = token_label  # type: ignore[assignment]
            # Select the right button based on current auth method
            codex_btn = self.query_one("#rb-auth-codex", RadioButton)
            apikey_btn = self.query_one("#rb-auth-apikey", RadioButton)
            codex_btn.value = self._auth_method == "codex"
            apikey_btn.value = self._auth_method != "codex"
        else:
            # No subscription option — always api_key
            self._auth_method = "api_key"

        self._refresh_auth_panes(info)

    def _refresh_auth_panes(self, info: dict | None = None) -> None:
        from vandelay.config.constants import MODEL_PROVIDERS

        if info is None:
            info = MODEL_PROVIDERS.get(self._provider, {})

        showing_codex = self._auth_method == "codex"

        # API key pane
        key_section = self.query_one("#auth-key-section")
        key_section.display = not showing_codex
        if not showing_codex:
            label = info.get("api_key_label") or "API key"
            hint = info.get("api_key_help") or ""
            self.query_one("#key-label", Label).update(f"{label}:")
            self.query_one("#key-hint", Static).update(f"  {hint}" if hint else "")

        # Codex / subscription pane
        codex_section = self.query_one("#auth-codex-section")
        codex_section.display = showing_codex
        if showing_codex:
            from pathlib import Path
            codex_auth = Path.home() / ".codex" / "auth.json"
            if codex_auth.exists():
                self.query_one("#codex-status", Static).update(
                    f"[green]✓[/green] Credentials found at {codex_auth}\n"
                    "[dim]Vandelay will read and auto-refresh this token at runtime.[/dim]"
                )
            else:
                token_help = info.get("token_help") or ""
                self.query_one("#codex-status", Static).update(
                    f"[yellow]⚠[/yellow] {codex_auth} not found.\n"
                    "[dim]You can still continue — set up Codex before starting the server.[/dim]"
                )
                self.query_one("#codex-hint", Static).update(f"  {token_help}" if token_help else "")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "radio-auth":
            # Index 0 = codex, Index 1 = api_key
            self._auth_method = "codex" if event.index == 0 else "api_key"
            from vandelay.config.constants import MODEL_PROVIDERS
            self._refresh_auth_panes(MODEL_PROVIDERS.get(self._provider, {}))

    # ------------------------------------------------------------------ #
    # Collect / validate                                                   #
    # ------------------------------------------------------------------ #

    def _collect_current(self) -> bool:
        """Read current step's input into instance state. Returns False on error."""
        error = self.query_one("#onboard-error", Static)

        if self._step == 0:
            name = self.query_one("#input-name", Input).value.strip()
            if not name:
                error.update("[red]Agent name is required.[/red]")
                return False
            self._agent_name = name

        elif self._step == 1:
            # RadioSet — find selected
            try:
                rs = self.query_one("#radio-provider", RadioSet)
                # RadioSet.pressed_index → index of selected button
                idx = rs.pressed_index
                if idx is not None and 0 <= idx < len(_PROVIDER_ORDER):
                    self._provider = _PROVIDER_ORDER[idx]
            except Exception:
                pass  # keep default

        elif self._step == 2:
            if self._auth_method == "codex":
                self._api_key = ""  # no key needed for subscription route
            else:
                self._api_key = self.query_one("#input-key", Input).value.strip()

        elif self._step == 3:
            tz = self.query_one("#input-tz", Input).value.strip() or "UTC"
            self._timezone = tz

        return True

    # ------------------------------------------------------------------ #
    # Finish                                                               #
    # ------------------------------------------------------------------ #

    def _finish(self) -> None:
        if not self._collect_current():
            return

        try:
            self._apply_settings()
        except Exception as exc:
            logger.exception("Onboarding failed: %s", exc)
            self.query_one("#onboard-error", Static).update(
                f"[red]Setup failed: {exc}[/red]"
            )
            return

        self.dismiss(None)

    def _apply_settings(self) -> None:
        from vandelay.config.constants import MODEL_PROVIDERS
        from vandelay.config.settings import Settings, get_settings
        from vandelay.workspace.manager import init_workspace

        info = MODEL_PROVIDERS[self._provider]

        # Codex OAuth uses a different model ID than the standard provider default
        if self._auth_method == "codex":
            model_id = "gpt-5.1-codex-mini"
        else:
            model_id = info["default_model"]

        s = Settings()
        s.agent_name = self._agent_name
        s.model.provider = self._provider
        s.model.model_id = model_id
        s.model.auth_method = self._auth_method
        s.timezone = self._timezone
        s.save()

        # Bust the lru_cache so the rest of the TUI picks up the new settings
        get_settings.cache_clear()

        if self._api_key and self._auth_method == "api_key":
            env_key = info.get("env_key")
            if env_key:
                from vandelay.cli.onboard import _write_env_key

                _write_env_key(env_key, self._api_key)

        init_workspace()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _detect_tz() -> str:
    try:
        from vandelay.cli.onboard import _detect_system_timezone

        return _detect_system_timezone() or "UTC"
    except Exception:
        return "UTC"
