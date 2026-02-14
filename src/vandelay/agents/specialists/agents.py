"""Specialist agent factories — DEPRECATED.

Member creation is now handled by ``_resolve_member()`` and
``_build_member_agent()`` in ``vandelay.agents.factory``.

Legacy string member names ("browser", "system", "scheduler", "knowledge")
are resolved via ``_LEGACY_TOOL_MAP`` and ``_LEGACY_ROLE_MAP`` in the factory
module, so existing configs continue to work without this file.
"""
