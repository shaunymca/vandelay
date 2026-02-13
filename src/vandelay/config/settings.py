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
from vandelay.routing.config import RouterConfig


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
    router: RouterConfig = Field(default_factory=RouterConfig)

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
                # File values are the base; explicit values override
                merged = {**file_data, **{k: v for k, v in values.items() if v is not None}}
                values = merged
            except (json.JSONDecodeError, OSError):
                pass

        # Map VANDELAY_HOST/PORT/SECRET_KEY env vars into nested server config
        cls._apply_env_to_server(values)
        return values

    @classmethod
    def _apply_env_to_server(cls, values: dict) -> None:
        """Map flat VANDELAY_HOST/PORT/SECRET_KEY env vars into server sub-config."""
        import os

        env_map = {
            "VANDELAY_HOST": "host",
            "VANDELAY_PORT": "port",
            "VANDELAY_SECRET_KEY": "secret_key",
        }

        # Also check ~/.vandelay/.env for these values
        env_file_vals: dict[str, str] = {}
        env_path = VANDELAY_HOME / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    k = k.strip()
                    if " #" in v:
                        v = v[:v.index(" #")]
                    env_file_vals[k] = v.strip()
            except OSError:
                pass

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
