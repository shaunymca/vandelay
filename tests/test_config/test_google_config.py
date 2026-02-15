"""Tests for GoogleConfig model."""

from vandelay.config.models import GoogleConfig


class TestGoogleConfig:
    def test_defaults(self):
        cfg = GoogleConfig()
        assert cfg.calendar_id == "primary"

    def test_custom_calendar_id(self):
        cfg = GoogleConfig(calendar_id="shaun@gmail.com")
        assert cfg.calendar_id == "shaun@gmail.com"

    def test_serialization_roundtrip(self):
        cfg = GoogleConfig(calendar_id="team@example.com")
        data = cfg.model_dump()
        restored = GoogleConfig(**data)
        assert restored.calendar_id == "team@example.com"
