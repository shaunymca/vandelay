"""First-run modal — shown when no config exists."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

_WORDMARK = """\
    ╦  ╦╔═╗╔╗╔╔╦╗╔═╗╦  ╔═╗╦ ╦
    ╚╗╔╝╠═╣║║║ ║║║╣ ║  ╠═╣╚╦╝
    ╚╝ ╩ ╩╝╚╝═╩╝╚═╝╩═╝╩ ╩ ╩"""


class FirstRunModal(ModalScreen[str]):
    """Welcome modal with 'Onboard' and 'I know what I'm doing' choices."""

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Static(_WORDMARK, id="modal-wordmark")
            yield Label("The employee who doesn't exist.", id="modal-tagline")
            yield Label(
                "Welcome! Let's get you set up before we open the dashboard.",
                id="modal-message",
            )
            with Horizontal(id="modal-buttons"):
                yield Button("  Onboard  ", id="btn-onboard", variant="primary")
                yield Button(" I know what I'm doing ", id="btn-skip", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id.removeprefix("btn-"))
