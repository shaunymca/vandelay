"""Central settings — loads from ~/.vandelay/config.json + environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from vandelay.config.constants import (
    CONFIG_FILE,
    DB_DIR,
    DEFAULT_DB_FILE,
    VANDELAY_HOME,
    WORKSPACE_DIR,
)
from vandelay.config.models import (
    SECRET_FIELD_ENV_MAP,
    ChannelConfig,
    DeepWorkConfig,
    HeartbeatConfig,
    KnowledgeConfig,
    ModelConfig,
    SafetyConfig,
    ServerConfig,
    TeamConfig,
)


class Settings(BaseSettings):
    """All vandelay configuration in one place.

    Priority (highest → lowest):
      1. Environment variables (VANDELAY_ prefix)
      2. .env file
      3. ~/.vandelay/config.json
      4. Defaults defined here
    """

    model_config = SettingsConfigDict(
        env_prefix="VANDELAY_",
        env_file=(".env", str(VANDELAY_HOME / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Sub-configs ---
    model: ModelConfig = Field(default_factory=ModelConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    channels: ChannelConfig = Field(default_factory=ChannelConfig)
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    deep_work: DeepWorkConfig = Field(default_factory=DeepWorkConfig)
    team: TeamConfig = Field(default_factory=TeamConfig)

    # --- Top-level settings ---
    agent_name: str = "Art"
    user_id: str = ""  # Email or identifier — shared across all channels
    timezone: str = "UTC"
    db_url: str = ""  # empty = use SQLite at default path
    workspace_dir: str = str(WORKSPACE_DIR)
    enabled_tools: list[str] = Field(default_factory=list)  # e.g. ["shell", "file", "python"]

    @model_validator(mode="before")
    @classmethod
    def load_config_file(cls, values: dict) -> dict:
        """Merge config.json values as defaults (env vars still override)."""
        if CONFIG_FILE.exists():
            try:
                file_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                # Migrate any secrets out of config.json into .env
                cls._migrate_secrets_from_config(file_data)
                # File values are the base; explicit values override
                merged = {**file_data, **{k: v for k, v in values.items() if v is not None}}
                values = merged
            except (json.JSONDecodeError, OSError):
                pass

        # Populate secret fields from env vars / .env
        cls._apply_env_to_secrets(values)
        # Map VANDELAY_HOST/PORT env vars into nested server config
        cls._apply_env_to_server(values)
        return values

    @classmethod
    def _migrate_secrets_from_config(cls, file_data: dict) -> None:
        """Move any secrets found in config.json into .env and strip them.

        Runs once per load — only writes to .env if secrets are actually present
        in the JSON data. After migration, re-writes config.json without the
        secret values.
        """
        from vandelay.config.env_utils import write_env_key

        migrated = False
        for key_path, env_var in SECRET_FIELD_ENV_MAP.items():
            # Walk into the nested dict
            node = file_data
            for part in key_path[:-1]:
                node = node.get(part, {})
                if not isinstance(node, dict):
                    node = {}
                    break

            field = key_path[-1]
            value = node.get(field, "")
            if value and isinstance(value, str):
                write_env_key(env_var, value)
                node[field] = ""
                migrated = True

        if migrated:
            # Re-write config.json without the secrets
            CONFIG_FILE.write_text(
                json.dumps(file_data, indent=2), encoding="utf-8"
            )

    @classmethod
    def _apply_env_to_secrets(cls, values: dict) -> None:
        """Populate secret fields from environment variables and .env file."""
        import os

        from vandelay.config.env_utils import read_env_file

        env_file_vals = read_env_file()

        for key_path, env_var in SECRET_FIELD_ENV_MAP.items():
            val = os.environ.get(env_var) or env_file_vals.get(env_var)
            if not val:
                continue

            # Walk into the nested values dict, creating sub-dicts as needed
            node = values
            for part in key_path[:-1]:
                if part not in node or not isinstance(node[part], dict):
                    node[part] = {}
                node = node[part]

            node[key_path[-1]] = val

    @classmethod
    def _apply_env_to_server(cls, values: dict) -> None:
        """Map flat VANDELAY_HOST/PORT env vars into server sub-config."""
        import os

        from vandelay.config.env_utils import read_env_file

        env_map = {
            "VANDELAY_HOST": "host",
            "VANDELAY_PORT": "port",
        }

        env_file_vals = read_env_file()

        server = values.get("server", {})
        if not isinstance(server, dict):
            server = {}
        changed = False
        for env_key, field in env_map.items():
            val = os.environ.get(env_key) or env_file_vals.get(env_key)
            if val:
                server[field] = int(val) if field == "port" else val
                changed = True
        if changed:
            values["server"] = server

    @property
    def db_path(self) -> Path:
        """Resolved database path."""
        if self.db_url:
            return Path(self.db_url)
        DB_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_DB_FILE

    @property
    def is_postgres(self) -> bool:
        return self.db_url.startswith("postgresql")

    def save(self) -> None:
        """Persist current settings to config.json."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def config_exists(cls) -> bool:
        return CONFIG_FILE.exists()


@lru_cache
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
