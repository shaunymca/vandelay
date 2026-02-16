"""Tests for configuration models."""

from vandelay.config.models import (
    EmbedderConfig,
    KnowledgeConfig,
    ModelConfig,
    SafetyConfig,
)


class TestEmbedderConfig:
    def test_defaults(self):
        cfg = EmbedderConfig()
        assert cfg.provider == ""
        assert cfg.model == ""
        assert cfg.api_key == ""
        assert cfg.base_url == ""

    def test_explicit_values(self):
        cfg = EmbedderConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="sk-test",
            base_url="https://custom.endpoint",
        )
        assert cfg.provider == "openai"
        assert cfg.model == "text-embedding-3-small"
        assert cfg.api_key == "sk-test"
        assert cfg.base_url == "https://custom.endpoint"


class TestKnowledgeConfig:
    def test_defaults(self):
        cfg = KnowledgeConfig()
        assert cfg.enabled is True
        assert isinstance(cfg.embedder, EmbedderConfig)
        assert cfg.embedder.provider == ""

    def test_enabled_with_embedder(self):
        cfg = KnowledgeConfig(
            enabled=True,
            embedder=EmbedderConfig(provider="openai"),
        )
        assert cfg.enabled is True
        assert cfg.embedder.provider == "openai"

    def test_serialization_roundtrip(self):
        cfg = KnowledgeConfig(
            enabled=True,
            embedder=EmbedderConfig(provider="google", model="embedding-001"),
        )
        data = cfg.model_dump()
        restored = KnowledgeConfig(**data)
        assert restored.enabled is True
        assert restored.embedder.provider == "google"
        assert restored.embedder.model == "embedding-001"
