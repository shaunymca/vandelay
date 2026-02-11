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
    ChannelConfig,
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
    team: TeamConfig = Field(default_factory=TeamConfig)

    # --- Top-level settings ---
    agent_name: str = "Claw"
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
                # File values are the base; explicit values override
                merged = {**file_data, **{k: v for k, v in values.items() if v is not None}}
                return merged
            except (json.JSONDecodeError, OSError):
                pass
        return values

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
