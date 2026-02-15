"""Tests for ThreadRegistry persistence and session management."""

import json

import pytest

from vandelay.threads.registry import ThreadRegistry, _slugify


@pytest.fixture()
def registry(tmp_path):
    return ThreadRegistry(path=tmp_path / "threads.json")


class TestSlugify:
    def test_basic(self):
        assert _slugify("project-a") == "project-a"

    def test_special_chars(self):
        assert _slugify("My Project!") == "my-project"

    def test_consecutive_hyphens(self):
        assert _slugify("a   b") == "a-b"

    def test_max_length(self):
        long = "a" * 100
        assert len(_slugify(long)) == 50


class TestThreadRegistry:
    def test_new_registry_returns_default_session(self, registry):
        sid = registry.get_active_session_id("tg:123", "tg:123")
        assert sid == "tg:123"

    def test_switch_creates_thread(self, registry):
        sid, created = registry.switch_thread("tg:123", "project-a", "tg:123")
        assert created is True
        assert sid == "tg:123:thread:project-a"

    def test_switch_existing_thread(self, registry):
        registry.switch_thread("tg:123", "project-a", "tg:123")
        sid, created = registry.switch_thread("tg:123", "project-a", "tg:123")
        assert created is False
        assert sid == "tg:123:thread:project-a"

    def test_default_thread_preserves_session_id(self, registry):
        # First ensure context exists
        registry.get_active_session_id("tg:123", "tg:123")
        sid, created = registry.switch_thread("tg:123", "default", "tg:123")
        assert sid == "tg:123"

    def test_get_active_session_id_after_switch(self, registry):
        registry.switch_thread("tg:123", "project-a", "tg:123")
        sid = registry.get_active_session_id("tg:123", "tg:123")
        assert sid == "tg:123:thread:project-a"

    def test_get_active_thread_name(self, registry):
        assert registry.get_active_thread_name("tg:123") == "default"
        registry.switch_thread("tg:123", "project-a", "tg:123")
        assert registry.get_active_thread_name("tg:123") == "project-a"

    def test_list_threads(self, registry):
        registry.switch_thread("tg:123", "alpha", "tg:123")
        registry.switch_thread("tg:123", "beta", "tg:123")
        threads = registry.list_threads("tg:123")
        names = {t["name"] for t in threads}
        # Should contain default + alpha + beta
        assert "default" in names
        assert "alpha" in names
        assert "beta" in names
        # beta is active (last switched to)
        active = [t for t in threads if t["active"]]
        assert len(active) == 1
        assert active[0]["name"] == "beta"

    def test_list_threads_empty_channel(self, registry):
        assert registry.list_threads("tg:999") == []

    def test_persistence_round_trip(self, tmp_path):
        path = tmp_path / "threads.json"
        reg1 = ThreadRegistry(path=path)
        reg1.switch_thread("tg:123", "project-a", "tg:123")

        reg2 = ThreadRegistry(path=path)
        sid = reg2.get_active_session_id("tg:123", "tg:123")
        assert sid == "tg:123:thread:project-a"

    def test_corrupt_file_recovery(self, tmp_path):
        path = tmp_path / "threads.json"
        path.write_text("not valid json!!!", encoding="utf-8")
        registry = ThreadRegistry(path=path)
        # Should recover gracefully — empty state
        sid = registry.get_active_session_id("tg:123", "tg:123")
        assert sid == "tg:123"

    def test_channels_isolated(self, registry):
        registry.switch_thread("tg:111", "project-a", "tg:111")
        registry.switch_thread("tg:222", "project-b", "tg:222")
        assert registry.get_active_thread_name("tg:111") == "project-a"
        assert registry.get_active_thread_name("tg:222") == "project-b"
