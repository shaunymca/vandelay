"""Tests for ChatService."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from vandelay.channels.base import IncomingMessage
from vandelay.core.chat_service import ChatResponse, ChatService, StreamChunk


def _make_incoming(text: str = "hello") -> IncomingMessage:
    return IncomingMessage(text=text, session_id="test-session", channel="test")


def _make_provider(agent: MagicMock):
    """Return a callable that returns the given agent."""
    return lambda: agent


class TestChatServiceRun:
    @pytest.mark.asyncio
    async def test_returns_content(self):
        agent = AsyncMock()
        response = MagicMock()
        response.content = "Hi there!"
        response.run_id = "run-1"
        agent.arun = AsyncMock(return_value=response)

        svc = ChatService(_make_provider(agent))
        result = await svc.run(_make_incoming("hello"))

        assert isinstance(result, ChatResponse)
        assert result.content == "Hi there!"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_empty_response(self):
        agent = AsyncMock()
        response = MagicMock()
        response.content = None
        agent.arun = AsyncMock(return_value=response)

        svc = ChatService(_make_provider(agent))
        result = await svc.run(_make_incoming())

        assert result.content == ""
        assert result.error is None

    @pytest.mark.asyncio
    async def test_agent_error_captured(self):
        agent = AsyncMock()
        agent.arun = AsyncMock(side_effect=RuntimeError("boom"))

        svc = ChatService(_make_provider(agent))
        result = await svc.run(_make_incoming())

        assert result.error == "boom"
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_calls_typing_indicator(self):
        agent = AsyncMock()
        response = MagicMock()
        response.content = "ok"

        # Simulate a brief delay so the typing loop has time to fire
        async def slow_arun(*args, **kwargs):
            await asyncio.sleep(0.05)
            return response

        agent.arun = slow_arun

        typing_fn = AsyncMock()
        svc = ChatService(_make_provider(agent))
        await svc.run(_make_incoming(), typing=typing_fn)

        assert typing_fn.await_count >= 1

    @pytest.mark.asyncio
    async def test_passes_user_id_and_session(self):
        agent = AsyncMock()
        response = MagicMock()
        response.content = "ok"
        agent.arun = AsyncMock(return_value=response)

        svc = ChatService(_make_provider(agent))
        msg = IncomingMessage(
            text="hi", session_id="sess-1", user_id="user-42", channel="telegram"
        )
        await svc.run(msg)

        agent.arun.assert_awaited_once_with(
            "hi", user_id="user-42", session_id="sess-1",
            images=None, audio=None, video=None, files=None,
        )

    @pytest.mark.asyncio
    async def test_resolves_agent_lazily(self):
        """Each run() call resolves the agent fresh from the provider."""
        agent_v1 = AsyncMock()
        r1 = MagicMock()
        r1.content = "v1"
        agent_v1.arun = AsyncMock(return_value=r1)

        agent_v2 = AsyncMock()
        r2 = MagicMock()
        r2.content = "v2"
        agent_v2.arun = AsyncMock(return_value=r2)

        ref = [agent_v1]
        svc = ChatService(lambda: ref[0])

        result1 = await svc.run(_make_incoming())
        assert result1.content == "v1"

        ref[0] = agent_v2
        result2 = await svc.run(_make_incoming())
        assert result2.content == "v2"


class TestChatServiceRunStream:
    @pytest.mark.asyncio
    async def test_yields_stream_chunks(self):
        """run_stream should yield StreamChunk objects from the agent's stream."""

        from agno.run.agent import RunEvent

        # Build a mock async iterator of agent chunks
        chunk1 = MagicMock()
        chunk1.event = RunEvent.run_content.value
        chunk1.content = "Hello "
        chunk1.run_id = "run-1"

        chunk2 = MagicMock()
        chunk2.event = RunEvent.run_content.value
        chunk2.content = "world"
        chunk2.run_id = "run-1"

        async def _fake_stream(*args, **kwargs):
            for c in [chunk1, chunk2]:
                yield c

        agent = MagicMock()
        agent.arun = _fake_stream

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for sc in svc.run_stream(_make_incoming()):
            chunks.append(sc)

        # Should have 2 content_delta + 1 content_done
        events = [c.event for c in chunks]
        assert events == ["content_delta", "content_delta", "content_done"]
        assert chunks[-1].content == "Hello world"

    @pytest.mark.asyncio
    async def test_stream_error_yields_run_error(self):
        """If the stream raises, run_stream yields a run_error chunk."""

        async def _exploding_stream(*args, **kwargs):
            raise RuntimeError("stream boom")
            yield  # make it an async generator  # noqa: E501

        agent = MagicMock()
        agent.arun = _exploding_stream

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for sc in svc.run_stream(_make_incoming()):
            chunks.append(sc)

        assert len(chunks) == 1
        assert chunks[0].event == "run_error"
        assert "stream boom" in chunks[0].content
