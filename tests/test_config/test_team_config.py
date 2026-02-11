"""Tests for TeamConfig model."""

from vandelay.config.models import TeamConfig


class TestTeamConfig:
    def test_defaults(self):
        cfg = TeamConfig()
        assert cfg.enabled is False
        assert cfg.members == ["browser", "system", "scheduler", "knowledge"]

    def test_enabled(self):
        cfg = TeamConfig(enabled=True)
        assert cfg.enabled is True

    def test_custom_members(self):
        cfg = TeamConfig(members=["browser", "system"])
        assert cfg.members == ["browser", "system"]

    def test_serialization_roundtrip(self):
        cfg = TeamConfig(enabled=True, members=["system", "knowledge"])
        data = cfg.model_dump()
        restored = TeamConfig(**data)
        assert restored.enabled is True
        assert restored.members == ["system", "knowledge"]
