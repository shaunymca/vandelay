"""Tests for config system."""

from unittest.mock import patch

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings


def test_default_settings(tmp_path):
    """Settings should have sane defaults when no config file exists."""
    fake_config = tmp_path / "config.json"
    with patch("vandelay.config.settings.CONFIG_FILE", fake_config):
        s = Settings()
        assert s.agent_name == "Art"
        assert s.model.provider == "anthropic"
        assert s.safety.mode == "confirm"


def test_settings_override():
    """Explicit values should override defaults."""
    s = Settings(
        agent_name="TestBot",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="trust"),
    )
    assert s.agent_name == "TestBot"
    assert s.model.provider == "ollama"
    assert s.safety.mode == "trust"


def test_settings_save_and_load(tmp_path):
    """Config should round-trip through JSON."""
    import json
    from vandelay.config.constants import CONFIG_FILE

    s = Settings(agent_name="RoundTrip")
    # Save to a temp config file
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(s.model_dump(mode="json"), indent=2))

    # Verify it's valid JSON
    data = json.loads(config_path.read_text())
    assert data["agent_name"] == "RoundTrip"
