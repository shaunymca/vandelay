"""Tests for secret field exclusion, migration, and env loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from vandelay.config.env_utils import read_env_file, write_env_key
from vandelay.config.models import ChannelConfig, EmbedderConfig, KnowledgeConfig, ServerConfig
from vandelay.config.settings import Settings

# ---------------------------------------------------------------------------
# write_env_key
# ---------------------------------------------------------------------------


class TestWriteEnvKey:
    def test_creates_new_file(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        write_env_key("FOO", "bar", env_path=env_path)
        assert env_path.read_text(encoding="utf-8").strip() == "FOO=bar"

    def test_appends_new_key(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("EXISTING=value\n", encoding="utf-8")
        write_env_key("NEW_KEY", "new_value", env_path=env_path)
        lines = env_path.read_text(encoding="utf-8").strip().splitlines()
        assert lines == ["EXISTING=value", "NEW_KEY=new_value"]

    def test_updates_existing_key(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("MY_KEY=old\nOTHER=keep\n", encoding="utf-8")
        write_env_key("MY_KEY", "updated", env_path=env_path)
        lines = env_path.read_text(encoding="utf-8").strip().splitlines()
        assert "MY_KEY=updated" in lines
        assert "OTHER=keep" in lines

    def test_creates_parent_dirs(self, tmp_path: Path):
        env_path = tmp_path / "sub" / "dir" / ".env"
        write_env_key("KEY", "val", env_path=env_path)
        assert env_path.exists()


# ---------------------------------------------------------------------------
# read_env_file
# ---------------------------------------------------------------------------


class TestReadEnvFile:
    def test_reads_kv_pairs(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("A=1\nB=hello\n", encoding="utf-8")
        result = read_env_file(env_path)
        assert result == {"A": "1", "B": "hello"}

    def test_strips_inline_comments(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("KEY=value # this is a comment\n", encoding="utf-8")
        result = read_env_file(env_path)
        assert result["KEY"] == "value"

    def test_skips_blank_and_comment_lines(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("# header\n\nKEY=val\n", encoding="utf-8")
        result = read_env_file(env_path)
        assert result == {"KEY": "val"}

    def test_returns_empty_for_missing_file(self, tmp_path: Path):
        result = read_env_file(tmp_path / "missing.env")
        assert result == {}


# ---------------------------------------------------------------------------
# model_dump excludes secret fields
# ---------------------------------------------------------------------------


class TestSecretExclusion:
    def test_channel_secrets_excluded_from_dump(self):
        cfg = ChannelConfig(
            telegram_enabled=True,
            telegram_bot_token="secret-token",
            telegram_chat_id="12345",
            whatsapp_enabled=True,
            whatsapp_access_token="wa-secret",
            whatsapp_phone_number_id="phone-id",
            whatsapp_verify_token="verify-secret",
            whatsapp_app_secret="app-secret",
        )
        data = cfg.model_dump()
        # Secrets must be absent
        assert "telegram_bot_token" not in data
        assert "whatsapp_access_token" not in data
        assert "whatsapp_verify_token" not in data
        assert "whatsapp_app_secret" not in data
        # Non-secrets must be present
        assert data["telegram_enabled"] is True
        assert data["telegram_chat_id"] == "12345"
        assert data["whatsapp_phone_number_id"] == "phone-id"

    def test_server_secret_key_excluded(self):
        cfg = ServerConfig(secret_key="super-secret")
        data = cfg.model_dump()
        assert "secret_key" not in data
        assert "host" in data
        assert "port" in data

    def test_embedder_api_key_excluded(self):
        cfg = EmbedderConfig(api_key="embed-secret", provider="openai")
        data = cfg.model_dump()
        assert "api_key" not in data
        assert data["provider"] == "openai"

    def test_settings_save_excludes_secrets(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        with patch("vandelay.config.settings.CONFIG_FILE", config_file):
            s = Settings(
                agent_name="Test",
                channels=ChannelConfig(
                    telegram_enabled=True,
                    telegram_bot_token="tok-123",
                ),
                server=ServerConfig(secret_key="s3cret"),
                knowledge=KnowledgeConfig(
                    embedder=EmbedderConfig(api_key="embed-key"),
                ),
            )
            s.save()
            saved = json.loads(config_file.read_text(encoding="utf-8"))
            assert saved["channels"].get("telegram_bot_token", "") == ""
            assert saved["server"].get("secret_key", "") == ""
            assert saved["knowledge"]["embedder"].get("api_key", "") == ""
            # Non-secret still present
            assert saved["channels"]["telegram_enabled"] is True


# ---------------------------------------------------------------------------
# Migration: secrets from config.json → .env
# ---------------------------------------------------------------------------


class TestSecretMigration:
    def test_migrate_moves_secrets_to_env(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        config_file = tmp_path / "config.json"

        config_data = {
            "agent_name": "Test",
            "channels": {
                "telegram_enabled": True,
                "telegram_bot_token": "tg-secret-123",
                "telegram_chat_id": "chat-id",
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "secret_key": "my-secret-key",
            },
            "knowledge": {
                "embedder": {
                    "api_key": "embed-key-456",
                },
            },
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with (
            patch("vandelay.config.settings.CONFIG_FILE", config_file),
            patch("vandelay.config.env_utils.VANDELAY_HOME", tmp_path),
            patch("vandelay.config.settings.VANDELAY_HOME", tmp_path),
        ):
            Settings._migrate_secrets_from_config(config_data)

            # Secrets should be in .env
            env_vals = read_env_file(env_path)
            assert env_vals["TELEGRAM_TOKEN"] == "tg-secret-123"
            assert env_vals["VANDELAY_SECRET_KEY"] == "my-secret-key"
            assert env_vals["VANDELAY_EMBEDDER_API_KEY"] == "embed-key-456"

            # Config data should have secrets cleared
            assert config_data["channels"]["telegram_bot_token"] == ""
            assert config_data["server"]["secret_key"] == ""
            assert config_data["knowledge"]["embedder"]["api_key"] == ""

            # Non-secrets untouched
            assert config_data["channels"]["telegram_enabled"] is True
            assert config_data["channels"]["telegram_chat_id"] == "chat-id"

    def test_no_migration_when_no_secrets(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        config_data = {
            "agent_name": "Test",
            "channels": {"telegram_enabled": False},
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with (
            patch("vandelay.config.settings.CONFIG_FILE", config_file),
            patch("vandelay.config.env_utils.VANDELAY_HOME", tmp_path),
        ):
            Settings._migrate_secrets_from_config(config_data)
            # .env should not be created if no secrets to migrate
            env_path = tmp_path / ".env"
            assert not env_path.exists()


# ---------------------------------------------------------------------------
# Secrets populated from env vars at runtime
# ---------------------------------------------------------------------------


class TestApplyEnvToSecrets:
    def test_populates_from_env_vars(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        env_vars = {
            "TELEGRAM_TOKEN": "env-tg-token",
            "VANDELAY_SECRET_KEY": "env-secret",
        }

        with (
            patch("vandelay.config.settings.CONFIG_FILE", config_file),
            patch("vandelay.config.settings.VANDELAY_HOME", tmp_path),
            patch("vandelay.config.env_utils.VANDELAY_HOME", tmp_path),
            patch.dict(os.environ, env_vars, clear=False),
        ):
            s = Settings()
            assert s.channels.telegram_bot_token == "env-tg-token"
            assert s.server.secret_key == "env-secret"

    def test_populates_from_env_file(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        env_path = tmp_path / ".env"
        env_path.write_text(
            "WHATSAPP_ACCESS_TOKEN=wa-from-file\n"
            "VANDELAY_EMBEDDER_API_KEY=embed-from-file\n",
            encoding="utf-8",
        )

        # Make sure these aren't in os.environ
        clean_env = {
            k: v for k, v in os.environ.items()
            if k not in ("WHATSAPP_ACCESS_TOKEN", "VANDELAY_EMBEDDER_API_KEY")
        }

        with (
            patch("vandelay.config.settings.CONFIG_FILE", config_file),
            patch("vandelay.config.settings.VANDELAY_HOME", tmp_path),
            patch("vandelay.config.env_utils.VANDELAY_HOME", tmp_path),
            patch.dict(os.environ, clean_env, clear=True),
        ):
            s = Settings()
            assert s.channels.whatsapp_access_token == "wa-from-file"
            assert s.knowledge.embedder.api_key == "embed-from-file"
