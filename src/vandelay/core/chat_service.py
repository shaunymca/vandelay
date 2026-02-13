"""ChatService — single pipeline for all agent interactions."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from agno.run.agent import RunEvent

from vandelay.channels.base import IncomingMessage
from vandelay.core.agent_provider import AgentProvider

logger = logging.getLogger("vandelay.core.chat_service")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ChatResponse:
    """Result of a non-streaming agent run."""

    content: str = ""
    run_id: str | None = None
    error: str | None = None


@dataclass
class StreamChunk:
    """A single event from a streaming agent run."""

    event: str = ""
    content: str = ""
    tool_name: str = ""
    tool_status: str = ""
    run_id: str | None = None


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

class TypingIndicator(Protocol):
    """Async callable that signals "agent is working" to the user."""

    async def __call__(self) -> None: ...


class ChatMiddleware(Protocol):
    """Pre/post hooks around agent runs (future use)."""

    async def before_run(self, message: IncomingMessage) -> None: ...

    async def after_run(
        self, message: IncomingMessage, response: ChatResponse
    ) -> None: ...


# ---------------------------------------------------------------------------
# ChatService
# ---------------------------------------------------------------------------

class ChatService:
    """Centralized agent interaction layer.

    Channels call ``run()`` or ``run_stream()`` instead of touching the
    agent directly. The agent is resolved lazily via *agent_provider*,
    which fixes the hot-reload stale-reference bug.
    """

    def __init__(
        self,
        agent_provider: AgentProvider,
        middleware: list[ChatMiddleware] | None = None,
    ) -> None:
        self._get_agent = agent_provider
        self._middleware = middleware or []

    # -- Non-streaming (Telegram, CLI) -------------------------------------

    async def run(
        self,
        message: IncomingMessage,
        typing: Callable[[], Awaitable[None]] | None = None,
    ) -> ChatResponse:
        """Run the agent and return the full response."""
        agent = self._get_agent()

        # Pre-hooks
        for mw in self._middleware:
            await mw.before_run(message)

        try:
            typing_task = None
            if typing:
                typing_task = asyncio.create_task(
                    _typing_loop(typing), name="typing-indicator"
                )

            response = await agent.arun(
                message.text,
                user_id=message.user_id or None,
                session_id=message.session_id,
            )

            if typing_task:
                typing_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await typing_task

            result = ChatResponse(
                content=response.content if response and response.content else "",
                run_id=getattr(response, "run_id", None),
            )
        except Exception as exc:
            logger.error("Agent error: %s", exc, exc_info=True)
            result = ChatResponse(error=str(exc))

        # Post-hooks
        for mw in self._middleware:
            await mw.after_run(message, result)

        return result

    # -- Chunked (Telegram, CLI) ---------------------------------------------

    async def run_chunked(
        self,
        message: IncomingMessage,
        typing: Callable[[], Awaitable[None]] | None = None,
        min_chunk_size: int = 80,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Stream internally and yield logical paragraph-sized chunks.

        The agent is called in streaming mode. Token deltas are accumulated
        into a buffer. When a paragraph break (``\\n\\n``) is found outside a
        code fence and the buffer exceeds *min_chunk_size*, the accumulated
        text is yielded as a ``ChatResponse``. Any remaining text is yielded
        when the stream ends.
        """
        agent = self._get_agent()

        # Pre-hooks
        for mw in self._middleware:
            await mw.before_run(message)

        typing_task = None
        if typing:
            typing_task = asyncio.create_task(
                _typing_loop(typing), name="typing-indicator"
            )

        buffer = ""
        run_id: str | None = None
        full_content = ""
        yielded_any = False

        try:
            run_response = agent.arun(
                input=message.text,
                user_id=message.user_id or None,
                session_id=message.session_id,
                stream=True,
                stream_events=True,
            )

            async for chunk in run_response:
                event_type = getattr(chunk, "event", "")
                run_id = getattr(chunk, "run_id", run_id)

                if event_type == RunEvent.run_content.value:
                    delta = getattr(chunk, "content", "")
                    if delta:
                        buffer += str(delta)

                    # Try to split at paragraph breaks outside code fences
                    while "\n\n" in buffer:
                        idx = buffer.index("\n\n")
                        candidate = buffer[:idx]

                        # Don't split inside code fences
                        if _inside_code_fence(candidate):
                            # Move past this \n\n and keep scanning
                            next_after = idx + 2
                            # Look for next \n\n
                            next_break = buffer.find("\n\n", next_after)
                            if next_break == -1:
                                break  # wait for more data
                            idx = next_break
                            candidate = buffer[:idx]
                            if _inside_code_fence(candidate):
                                break  # still inside — wait

                        if len(candidate.strip()) >= min_chunk_size:
                            text = candidate.strip()
                            full_content += text + "\n\n"
                            yield ChatResponse(content=text, run_id=run_id)
                            yielded_any = True
                            buffer = buffer[idx + 2:]
                        else:
                            # Too small — keep accumulating
                            break

                elif event_type == RunEvent.run_error.value:
                    error_msg = getattr(chunk, "content", "Unknown error")
                    yield ChatResponse(error=str(error_msg), run_id=run_id)
                    return

            # Flush remaining buffer
            remainder = buffer.strip()
            if remainder:
                full_content += remainder
                yield ChatResponse(content=remainder, run_id=run_id)
                yielded_any = True

            if not yielded_any:
                yield ChatResponse(content="", run_id=run_id)

        except Exception as exc:
            logger.error("Chunked stream error: %s", exc, exc_info=True)
            yield ChatResponse(error=str(exc))
        finally:
            if typing_task:
                typing_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await typing_task

        # Post-hooks (use full accumulated content)
        result = ChatResponse(content=full_content.strip(), run_id=run_id)
        for mw in self._middleware:
            await mw.after_run(message, result)

    # -- Streaming (WebSocket) ---------------------------------------------

    async def run_stream(
        self,
        message: IncomingMessage,
        typing: Callable[[], Awaitable[None]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream agent response as ``StreamChunk`` events."""
        agent = self._get_agent()

        typing_task = None
        if typing:
            typing_task = asyncio.create_task(
                _typing_loop(typing), name="typing-indicator"
            )

        try:
            run_response = agent.arun(
                input=message.text,
                user_id=message.user_id or None,
                session_id=message.session_id,
                stream=True,
                stream_events=True,
            )

            full_content = ""
            run_id: str | None = None

            async for chunk in run_response:
                event_type = getattr(chunk, "event", "")
                run_id = getattr(chunk, "run_id", run_id)

                if event_type == RunEvent.run_content.value:
                    delta = getattr(chunk, "content", "")
                    if delta:
                        full_content += str(delta)
                        yield StreamChunk(
                            event="content_delta",
                            content=str(delta),
                            run_id=run_id,
                        )

                elif event_type == RunEvent.run_error.value:
                    error_msg = getattr(chunk, "content", "Unknown error")
                    yield StreamChunk(
                        event="run_error",
                        content=str(error_msg),
                        run_id=run_id,
                    )
                    return

                elif event_type == RunEvent.tool_call_started.value:
                    tool = getattr(chunk, "tool", None)
                    tool_name = (
                        getattr(tool, "tool_name", "unknown") if tool else "unknown"
                    )
                    yield StreamChunk(
                        event="tool_call",
                        tool_name=tool_name,
                        tool_status="started",
                        run_id=run_id,
                    )

                elif event_type == RunEvent.tool_call_completed.value:
                    tool = getattr(chunk, "tool", None)
                    tool_name = (
                        getattr(tool, "tool_name", "unknown") if tool else "unknown"
                    )
                    yield StreamChunk(
                        event="tool_call",
                        tool_name=tool_name,
                        tool_status="completed",
                        run_id=run_id,
                    )

            # Final chunk signals stream completion
            yield StreamChunk(
                event="content_done",
                content=full_content,
                run_id=run_id,
            )

        except Exception as exc:
            logger.error("Stream error: %s", exc, exc_info=True)
            yield StreamChunk(event="run_error", content=str(exc))
        finally:
            if typing_task:
                typing_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await typing_task


def _inside_code_fence(text: str) -> bool:
    """Return True if *text* has an odd number of ``` fences (i.e. unclosed)."""
    return text.count("```") % 2 != 0


async def _typing_loop(
    typing_fn: Callable[[], Awaitable[None]],
    interval: float = 4.0,
) -> None:
    """Repeatedly send typing indicator until cancelled.

    Telegram's typing status expires after ~5 seconds, so we resend
    every *interval* seconds to keep it visible during long runs.
    """
    while True:
        await typing_fn()
        await asyncio.sleep(interval)
