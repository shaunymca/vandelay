"""Chat tab — real-time chat with the agent via WebSocket."""

from __future__ import annotations

import asyncio
import json
import logging

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Markdown, Static


class _HRow(Widget):
    """Horizontal row that fills its grid cell.

    Horizontal.DEFAULT_CSS has `height: auto` which causes it to render as
    height=0 inside a grid cell (it ignores the allocated region height).
    Widget has no such default, so the grid's row height is honoured.
    """

    DEFAULT_CSS = "_HRow { layout: horizontal; overflow: hidden hidden; }"

logger = logging.getLogger("vandelay.tui.chat")

_RECONNECT_DELAY = 3.0


class ChatTab(Widget):
    """Real-time chat with the agent — connects to /ws/terminal.

    Uses CSS grid layout (grid-rows: 1 1fr 3) so the log fills the
    available space between the fixed status bar and input bar reliably.
    """

    DEFAULT_CSS = """
    ChatTab { height: 1fr; }
    """

    # ------------------------------------------------------------------
    # Textual messages — posted from WS task, handled on event loop
    # ------------------------------------------------------------------

    class Connected(Message):
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    class Disconnected(Message):
        pass

    class ContentDelta(Message):
        def __init__(self, content: str) -> None:
            super().__init__()
            self.content = content

    class ContentDone(Message):
        def __init__(self, full_content: str) -> None:
            super().__init__()
            self.full_content = full_content

    class ToolStarted(Message):
        def __init__(self, tool: str) -> None:
            super().__init__()
            self.tool = tool

    class ToolDone(Message):
        def __init__(self, tool: str) -> None:
            super().__init__()
            self.tool = tool

    class RunError(Message):
        def __init__(self, error: str) -> None:
            super().__init__()
            self.error = error

    class SystemInfo(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class SessionReset(Message):
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    # ------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self._host = "127.0.0.1"
        self._port = 8000
        self._secret_key = ""
        self._agent_name = "Agent"
        self._load_settings()
        self._session_id = ""
        self._ws = None
        self._ws_task: asyncio.Task | None = None
        self._stream_widget: Markdown | None = None
        self._stream_buf = ""
        self._tool_widget: Static | None = None
        self._connected = False

    def _load_settings(self) -> None:
        try:
            from vandelay.config.settings import Settings, get_settings

            if Settings.config_exists():
                s = get_settings()
                host = s.server.host
                self._host = "127.0.0.1" if host == "0.0.0.0" else host
                self._port = s.server.port
                self._secret_key = s.server.secret_key or ""
                self._agent_name = s.agent_name or "Agent"
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        # Grid rows: auto/1 (status bar) | 1fr (log) | auto/3 (input bar)
        with _HRow(id="chat-status-bar"):
            yield Static("○", id="chat-conn-dot")
            yield Static("Connecting…", id="chat-session-label")
            yield Button("/new", id="chat-new-btn")
        with VerticalScroll(id="chat-log"):
            yield Static(
                "[dim]Waiting for server…[/dim]",
                id="chat-placeholder",
            )
        with _HRow(id="input-bar"):
            yield Input(
                placeholder="Message… (Enter to send,  /new to reset)",
                id="chat-input",
            )
            yield Button("Send", id="send-btn")

    def on_mount(self) -> None:
        self._start_ws()

    def on_show(self) -> None:
        self.query_one("#chat-input", Input).focus()

    # ------------------------------------------------------------------
    # WebSocket lifecycle
    # ------------------------------------------------------------------

    def _start_ws(self) -> None:
        if self._ws_task and not self._ws_task.done():
            return
        self._ws_task = asyncio.create_task(self._ws_loop(), name="chat-ws")

    async def _ws_loop(self) -> None:
        """Connect, read, auto-reconnect forever."""
        import websockets

        url = f"ws://{self._host}:{self._port}/ws/terminal"
        needs_auth = bool(
            self._secret_key
            and self._secret_key != "change-me-to-a-random-string"
        )

        while True:
            try:
                async with websockets.connect(url, open_timeout=5) as ws:
                    self._ws = ws
                    if needs_auth:
                        await ws.send(
                            json.dumps(
                                {"action": "authenticate", "token": self._secret_key}
                            )
                        )

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        ev = msg.get("event", "")

                        if ev == "session_started":
                            self.post_message(self.Connected(msg.get("session_id", "")))
                        elif ev == "content_delta":
                            self.post_message(self.ContentDelta(msg.get("content", "")))
                        elif ev == "content_done":
                            self.post_message(self.ContentDone(msg.get("content", "")))
                        elif ev == "tool_call":
                            status = msg.get("status", "")
                            tool = msg.get("tool", "")
                            if status == "started":
                                self.post_message(self.ToolStarted(tool))
                            else:
                                self.post_message(self.ToolDone(tool))
                        elif ev in ("run_error", "error"):
                            self.post_message(self.RunError(msg.get("error", ev)))
                        elif ev in ("thread_switched", "thread_current", "thread_list"):
                            sid = msg.get("session_id", self._session_id)
                            self.post_message(self.SystemInfo(msg.get("message", "")))
                            if sid and sid != self._session_id:
                                self._session_id = sid

            except Exception as exc:
                logger.debug("Chat WS error: %s", exc)
                self._ws = None

            self.post_message(self.Disconnected())
            await asyncio.sleep(_RECONNECT_DELAY)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    def on_chat_tab_connected(self, event: Connected) -> None:
        self._connected = True
        self._session_id = event.session_id
        self.query_one("#chat-conn-dot", Static).update("[green]●[/green]")
        short = event.session_id[-8:] if event.session_id else "—"
        self.query_one("#chat-session-label", Static).update(
            f"[green]Connected[/green]  [dim]#{short}[/dim]"
        )
        placeholder = self.query("#chat-placeholder")
        if placeholder:
            placeholder.first().display = False
        self.query_one("#chat-input", Input).focus()

    def on_chat_tab_disconnected(self, _: Disconnected) -> None:
        self._connected = False
        self._stream_widget = None
        self._tool_widget = None
        self.query_one("#chat-conn-dot", Static).update("[red]○[/red]")
        self.query_one("#chat-session-label", Static).update(
            "[red]Disconnected[/red]  [dim]retrying…[/dim]"
        )

    def on_chat_tab_content_delta(self, event: ContentDelta) -> None:
        if self._stream_widget is None:
            # Clear any tool indicator before the response starts
            if self._tool_widget is not None:
                self._tool_widget.remove()
                self._tool_widget = None
            self._stream_buf = ""
            self._append(
                Static(
                    f"[bold #3fb950]{self._agent_name}[/bold #3fb950]",
                    classes="msg-agent-name",
                )
            )
            w = Markdown("", classes="msg-agent")
            self._append(w)
            self._stream_widget = w
        self._stream_buf += event.content
        # Update fires async internally — use call_after_refresh to avoid flooding
        self._stream_widget.update(self._stream_buf)
        self._scroll_bottom()

    def on_chat_tab_content_done(self, event: ContentDone) -> None:
        if self._stream_widget is not None and event.full_content:
            self._stream_widget.update(event.full_content)
        self._stream_widget = None
        self._stream_buf = ""
        self._scroll_bottom()

    def on_chat_tab_tool_started(self, event: ToolStarted) -> None:
        if self._tool_widget is not None:
            self._tool_widget.remove()
        w = Static(f"⟳  {event.tool}…", classes="msg-tool")
        self._append(w)
        self._tool_widget = w
        self._scroll_bottom()

    def on_chat_tab_tool_done(self, _: ToolDone) -> None:
        if self._tool_widget is not None:
            self._tool_widget.remove()
            self._tool_widget = None

    def on_chat_tab_run_error(self, event: RunError) -> None:
        self._stream_widget = None
        self._tool_widget = None
        self._append(
            Static(f"[bold red]Error:[/bold red] {event.error}", classes="msg-error")
        )
        self._scroll_bottom()

    def on_chat_tab_system_info(self, event: SystemInfo) -> None:
        self._append(
            Static(f"[dim italic]{event.text}[/dim italic]", classes="msg-system")
        )
        self._scroll_bottom()

    def on_chat_tab_session_reset(self, event: SessionReset) -> None:
        self._session_id = event.session_id
        self._clear_log()
        self._append(
            Static(
                f"[dim]New session started  #{event.session_id[-8:]}[/dim]",
                classes="msg-system",
            )
        )

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            self._send()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            self._send()
        elif event.button.id == "chat-new-btn":
            self._new_session()

    def _send(self) -> None:
        inp = self.query_one("#chat-input", Input)
        text = inp.value.strip()
        if not text:
            return
        inp.value = ""

        if text == "/new":
            self._new_session()
            return

        if not self._connected or self._ws is None:
            self._append(
                Static(
                    "[red]Server is offline — start it first.[/red]",
                    classes="msg-error",
                )
            )
            return

        self._append(
            Static(f"[bold #58a6ff]You[/bold #58a6ff]  {text}", classes="msg-you")
        )
        self._scroll_bottom()

        asyncio.create_task(
            self._ws.send(
                json.dumps(
                    {"action": "chat", "text": text, "session_id": self._session_id}
                )
            )
        )

    def _new_session(self) -> None:
        if not self._connected or self._ws is None:
            return
        self._stream_widget = None
        self._tool_widget = None
        asyncio.create_task(
            self._ws.send(json.dumps({"action": "new_session"}))
        )
        self._clear_log()
        self._append(Static("[dim]New session started[/dim]", classes="msg-system"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _append(self, widget: Widget) -> None:
        self.query_one("#chat-log", VerticalScroll).mount(widget)

    def _scroll_bottom(self) -> None:
        self.query_one("#chat-log", VerticalScroll).scroll_end(animate=False)

    def _clear_log(self) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        for w in list(log.children):
            if getattr(w, "id", None) != "chat-placeholder":
                w.remove()
