"""Tests for ChatService.run_chunked()."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vandelay.channels.base import IncomingMessage
from vandelay.core.chat_service import ChatResponse, ChatService, _inside_code_fence


def _make_incoming(text: str = "hello") -> IncomingMessage:
    return IncomingMessage(text=text, session_id="test-session", channel="test")


def _make_provider(agent: MagicMock):
    return lambda: agent


def _make_stream_agent(text_deltas: list[str]) -> MagicMock:
    """Create a mock agent whose arun() returns an async generator of content events."""
    from agno.run.agent import RunEvent

    async def _fake_arun(*args, **kwargs):
        for delta in text_deltas:
            chunk = MagicMock()
            chunk.event = RunEvent.run_content.value
            chunk.content = delta
            chunk.run_id = "run-1"
            yield chunk

    agent = MagicMock()
    agent.arun = _fake_arun
    return agent


class TestRunChunked:
    @pytest.mark.asyncio
    async def test_two_paragraphs_yield_two_chunks(self):
        """Text with a paragraph break should yield two ChatResponse objects."""
        agent = _make_stream_agent([
            "First paragraph here with enough content to pass the threshold.",
            "\n\n",
            "Second paragraph also has enough content to be its own chunk.",
        ])

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming(), min_chunk_size=10):
            chunks.append(resp)

        assert len(chunks) == 2
        assert all(isinstance(c, ChatResponse) for c in chunks)
        assert "First paragraph" in chunks[0].content
        assert "Second paragraph" in chunks[1].content

    @pytest.mark.asyncio
    async def test_single_paragraph_yields_one_chunk(self):
        agent = _make_stream_agent(["Just one paragraph, no breaks at all."])

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming()):
            chunks.append(resp)

        assert len(chunks) == 1
        assert "Just one paragraph" in chunks[0].content

    @pytest.mark.asyncio
    async def test_code_block_not_split(self):
        """Content inside a code fence should not be split even with \\n\\n."""
        code_text = (
            "Here is some code:\n\n"
            "```python\ndef hello():\n    pass\n\n\nprint('hi')\n```"
            "\n\nDone."
        )
        agent = _make_stream_agent([code_text])

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming(), min_chunk_size=10):
            chunks.append(resp)

        # The code block should be kept together with surrounding text —
        # we expect 1-2 chunks but the code block itself must not be split
        all_content = " ".join(c.content for c in chunks)
        assert "```python" in all_content
        assert "```" in all_content
        # The code fence should appear in the same chunk
        code_chunk = [c for c in chunks if "```python" in c.content][0]
        assert "print('hi')" in code_chunk.content

    @pytest.mark.asyncio
    async def test_min_chunk_size_accumulates_small_paragraphs(self):
        """Tiny paragraphs should accumulate until they meet min_chunk_size."""
        agent = _make_stream_agent(["Hi\n\nOk\n\nThis is a long enough final paragraph."])

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming(), min_chunk_size=80):
            chunks.append(resp)

        # "Hi" and "Ok" are too small; everything should come as one chunk
        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_error_event_yields_error(self):
        """A stream error should yield a ChatResponse with error set."""
        from agno.run.agent import RunEvent

        async def _error_stream(*args, **kwargs):
            chunk = MagicMock()
            chunk.event = RunEvent.run_error.value
            chunk.content = "something broke"
            chunk.run_id = "run-err"
            yield chunk

        agent = MagicMock()
        agent.arun = _error_stream

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming()):
            chunks.append(resp)

        assert len(chunks) == 1
        assert chunks[0].error == "something broke"

    @pytest.mark.asyncio
    async def test_exception_yields_error(self):
        """If the agent raises, run_chunked yields an error ChatResponse."""
        async def _exploding(*args, **kwargs):
            raise RuntimeError("kaboom")
            yield  # noqa: E501

        agent = MagicMock()
        agent.arun = _exploding

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming()):
            chunks.append(resp)

        assert len(chunks) == 1
        assert chunks[0].error == "kaboom"

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """An empty stream should yield one empty ChatResponse."""
        async def _empty(*args, **kwargs):
            return
            yield  # noqa: E501

        agent = MagicMock()
        agent.arun = _empty

        svc = ChatService(_make_provider(agent))
        chunks = []
        async for resp in svc.run_chunked(_make_incoming()):
            chunks.append(resp)

        assert len(chunks) == 1
        assert chunks[0].content == ""
        assert chunks[0].error is None


class TestInsideCodeFence:
    def test_no_fences(self):
        assert _inside_code_fence("just text") is False

    def test_one_open_fence(self):
        assert _inside_code_fence("```python\ndef foo():") is True

    def test_closed_fence(self):
        assert _inside_code_fence("```\ncode\n```") is False

    def test_two_open_fences(self):
        assert _inside_code_fence("```\ncode\n```\nmore\n```") is True
