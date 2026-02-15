"""Persistent thread registry — maps thread names to Agno session IDs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from vandelay.config.constants import THREADS_FILE

MAX_THREAD_NAME_LEN = 50


def _slugify(name: str) -> str:
    """Convert a thread name to a safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug[:MAX_THREAD_NAME_LEN]


@dataclass
class ThreadInfo:
    session_id: str
    created_at: str  # ISO 8601 UTC
    last_active: str  # ISO 8601 UTC


@dataclass
class ChannelThreads:
    active: str = "default"
    threads: dict[str, ThreadInfo] = field(default_factory=dict)


class ThreadRegistry:
    """Persistent mapping of channel → {thread_name → session_id}."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or THREADS_FILE
        self._data: dict[str, ChannelThreads] = {}
        self._load()

    # -- Public API ----------------------------------------------------------

    def get_active_session_id(
        self, channel_key: str, default_session_id: str
    ) -> str:
        """Return the session_id for the current active thread."""
        ctx = self._ensure_context(channel_key, default_session_id)
        info = ctx.threads.get(ctx.active)
        if info is None:
            return default_session_id
        now = datetime.now(UTC).isoformat()
        info.last_active = now
        self._save()
        return info.session_id

    def switch_thread(
        self, channel_key: str, thread_name: str, base_session_id: str
    ) -> tuple[str, bool]:
        """Switch to a named thread, creating it if new.

        Returns ``(session_id, was_created)``.
        """
        ctx = self._ensure_context(channel_key, base_session_id)
        slug = _slugify(thread_name) if thread_name != "default" else "default"
        now = datetime.now(UTC).isoformat()

        created = False
        if slug not in ctx.threads:
            sid = base_session_id if slug == "default" else f"{base_session_id}:thread:{slug}"
            ctx.threads[slug] = ThreadInfo(
                session_id=sid, created_at=now, last_active=now
            )
            created = True

        ctx.active = slug
        ctx.threads[slug].last_active = now
        self._save()
        return ctx.threads[slug].session_id, created

    def get_active_thread_name(self, channel_key: str) -> str:
        """Return the name of the active thread."""
        ctx = self._data.get(channel_key)
        if ctx is None:
            return "default"
        return ctx.active

    def list_threads(self, channel_key: str) -> list[dict]:
        """Return all threads sorted by last_active descending."""
        ctx = self._data.get(channel_key)
        if ctx is None:
            return []
        result = []
        for name, info in ctx.threads.items():
            result.append({
                "name": name,
                "session_id": info.session_id,
                "created_at": info.created_at,
                "last_active": info.last_active,
                "active": name == ctx.active,
            })
        result.sort(key=lambda t: t["last_active"], reverse=True)
        return result

    # -- Internal ------------------------------------------------------------

    def _ensure_context(
        self, channel_key: str, base_session_id: str
    ) -> ChannelThreads:
        """Lazy-init a channel's thread context with a 'default' thread."""
        if channel_key not in self._data:
            now = datetime.now(UTC).isoformat()
            ctx = ChannelThreads(
                active="default",
                threads={
                    "default": ThreadInfo(
                        session_id=base_session_id,
                        created_at=now,
                        last_active=now,
                    )
                },
            )
            self._data[channel_key] = ctx
            self._save()
        return self._data[channel_key]

    def _load(self) -> None:
        """Load registry from disk."""
        if not self._path.exists():
            self._data = {}
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for key, val in raw.items():
                threads = {}
                for tname, tinfo in val.get("threads", {}).items():
                    threads[tname] = ThreadInfo(
                        session_id=tinfo["session_id"],
                        created_at=tinfo["created_at"],
                        last_active=tinfo["last_active"],
                    )
                self._data[key] = ChannelThreads(
                    active=val.get("active", "default"),
                    threads=threads,
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            self._data = {}

    def _save(self) -> None:
        """Persist registry to disk."""
        out: dict = {}
        for key, ctx in self._data.items():
            threads = {}
            for tname, info in ctx.threads.items():
                threads[tname] = {
                    "session_id": info.session_id,
                    "created_at": info.created_at,
                    "last_active": info.last_active,
                }
            out[key] = {"active": ctx.active, "threads": threads}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(out, indent=2), encoding="utf-8"
        )
