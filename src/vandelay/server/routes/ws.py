"""WebSocket terminal endpoint for bidirectional chat."""

from __future__ import annotations

import contextlib
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from vandelay.channels.base import IncomingMessage

logger = logging.getLogger("vandelay.server.ws")

ws_router = APIRouter()


class WSConnection:
    """Tracks state for a single WebSocket terminal session."""

    def __init__(self, websocket: WebSocket, session_id: str) -> None:
        self.websocket = websocket
        self.session_id = session_id
        self.authenticated = False

    async def send_event(self, event: str, **data) -> None:
        """Send a JSON event to the client."""
        await self.websocket.send_json({"event": event, **data})


def _auth_required(settings) -> bool:
    """Check if secret_key auth is required."""
    key = settings.server.secret_key
    return bool(key) and key != "change-me-to-a-random-string"


@ws_router.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket) -> None:
    """Bidirectional WebSocket for terminal-style chat with the agent."""
    await websocket.accept()

    settings = websocket.app.state.settings
    chat_service = websocket.app.state.chat_service
    requires_auth = _auth_required(settings)

    session_id = f"ws-{uuid.uuid4().hex[:8]}"
    conn = WSConnection(websocket, session_id)

    # Skip auth when using default secret key
    if not requires_auth:
        conn.authenticated = True

    await conn.send_event("session_started", session_id=session_id)

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await conn.send_event("error", error="Invalid JSON")
                continue

            action = msg.get("action", "")

            # --- Authenticate ---
            if action == "authenticate":
                token = msg.get("token", "")
                if token == settings.server.secret_key:
                    conn.authenticated = True
                    await conn.send_event("auth_ok")
                else:
                    await conn.send_event("auth_error", error="Invalid token")
                continue

            # Guard: all other actions require auth
            if requires_auth and not conn.authenticated:
                await conn.send_event(
                    "auth_required",
                    error="Send authenticate action first.",
                )
                continue

            # --- Ping ---
            if action == "ping":
                await conn.send_event("pong")
                continue

            # --- New session ---
            if action == "new_session":
                conn.session_id = f"ws-{uuid.uuid4().hex[:8]}"
                await conn.send_event(
                    "session_started", session_id=conn.session_id
                )
                continue

            # --- Chat ---
            if action == "chat":
                text = msg.get("text", "").strip()
                if not text:
                    await conn.send_event("error", error="Empty message")
                    continue

                # Intercept /thread commands
                registry = getattr(websocket.app.state, "thread_registry", None)
                if registry and text.startswith("/thread"):
                    from vandelay.threads.commands import parse_thread_command

                    cmd = parse_thread_command(text)
                    channel_key = f"ws:{settings.user_id or 'default'}"
                    base_sid = conn.session_id

                    if cmd.action == "switch":
                        sid, created = registry.switch_thread(
                            channel_key, cmd.thread_name, base_sid
                        )
                        conn.session_id = sid
                        verb = "Created and switched to" if created else "Switched to"
                        await conn.send_event(
                            "thread_switched",
                            thread=cmd.thread_name,
                            session_id=sid,
                            created=created,
                            message=f"{verb} thread: {cmd.thread_name}",
                        )
                        continue
                    elif cmd.action == "show_current":
                        name = registry.get_active_thread_name(channel_key)
                        await conn.send_event(
                            "thread_current",
                            thread=name,
                            message=f"Current thread: {name}",
                        )
                        continue
                    elif cmd.action == "list":
                        threads = registry.list_threads(channel_key)
                        await conn.send_event(
                            "thread_list",
                            threads=threads,
                            message="Thread list",
                        )
                        continue

                # Allow client to override session_id to resume a session
                sid = msg.get("session_id") or conn.session_id
                await _handle_chat(chat_service, conn, text, sid, settings)
                continue

            await conn.send_event("error", error=f"Unknown action: {action}")

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected: session=%s", conn.session_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e, exc_info=True)
        if websocket.client_state == WebSocketState.CONNECTED:
            with contextlib.suppress(Exception):
                await conn.send_event("error", error=str(e))


async def _handle_chat(
    chat_service, conn: WSConnection, text: str, session_id: str, settings
) -> None:
    """Stream agent response over WebSocket via ChatService."""
    incoming = IncomingMessage(
        text=text,
        session_id=session_id,
        user_id=settings.user_id or "default",
        channel="websocket",
    )

    try:
        async for chunk in chat_service.run_stream(incoming):
            if chunk.event == "content_delta":
                await conn.send_event(
                    "content_delta",
                    content=chunk.content,
                    agent_name=settings.agent_name,
                )
            elif chunk.event == "run_error":
                await conn.send_event("run_error", error=chunk.content)
                return
            elif chunk.event == "tool_call":
                await conn.send_event(
                    "tool_call",
                    tool=chunk.tool_name,
                    status=chunk.tool_status,
                )
            elif chunk.event == "content_done":
                await conn.send_event(
                    "content_done",
                    content=chunk.content,
                    session_id=session_id,
                    run_id=chunk.run_id,
                )

    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        await conn.send_event("run_error", error=str(e))
