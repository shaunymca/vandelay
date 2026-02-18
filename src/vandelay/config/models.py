"""Pydantic models for configuration sub-sections."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ModelConfig(BaseModel):
    """Which LLM provider and model to use."""

    provider: str = "anthropic"
    model_id: str = "claude-sonnet-4-5-20250929"
    auth_method: str = "api_key"  # "api_key" or "token"


class SafetyConfig(BaseModel):
    """Shell command safety settings."""

    mode: str = "confirm"  # trust | confirm | tiered
    allowed_commands: list[str] = Field(
        default_factory=lambda: [
            "ls", "cat", "head", "tail", "grep", "find", "wc",
            "date", "whoami", "hostname", "uname", "df", "du",
            "pwd", "echo", "env", "printenv", "which", "file",
            "git status", "git log", "git diff", "git branch",
        ]
    )
    blocked_patterns: list[str] = Field(
        default_factory=lambda: [
            "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:",
            "chmod -R 777 /", "shutdown", "reboot", "halt",
            # Prevent agent from editing its own source code
            "src/vandelay", "src\\vandelay",
        ]
    )
    command_timeout_seconds: int = 120


class ChannelConfig(BaseModel):
    """Messaging channel settings."""

    telegram_enabled: bool = False
    telegram_bot_token: str = Field(default="", exclude=True)
    telegram_chat_id: str = ""

    whatsapp_enabled: bool = False
    whatsapp_access_token: str = Field(default="", exclude=True)
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = Field(default="", exclude=True)
    whatsapp_app_secret: str = Field(default="", exclude=True)


class HeartbeatConfig(BaseModel):
    """Heartbeat / proactive wake settings."""

    enabled: bool = False
    interval_minutes: int = 30
    active_hours_start: int = 8   # 24h format
    active_hours_end: int = 22
    timezone: str = "UTC"

    @model_validator(mode="after")
    def validate_active_hours(self) -> "HeartbeatConfig":
        if not 0 <= self.active_hours_start <= 23:
            raise ValueError(f"active_hours_start must be 0-23, got {self.active_hours_start}")
        if not 0 <= self.active_hours_end <= 23:
            raise ValueError(f"active_hours_end must be 0-23, got {self.active_hours_end}")
        if self.active_hours_start >= self.active_hours_end:
            raise ValueError(
                f"active_hours_start ({self.active_hours_start}) must be less than "
                f"active_hours_end ({self.active_hours_end})"
            )
        return self


class ServerConfig(BaseModel):
    """HTTP server settings."""

    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = Field(default="change-me-to-a-random-string", exclude=True)


class EmbedderConfig(BaseModel):
    """Explicit embedder override. When empty, auto-matches model provider."""

    provider: str = ""  # openai | google | ollama | "" (auto)
    model: str = ""  # e.g. "text-embedding-3-small"
    api_key: str = Field(default="", exclude=True)  # only if different from model provider
    base_url: str = ""  # custom endpoint


class KnowledgeConfig(BaseModel):
    """Knowledge/RAG settings."""

    enabled: bool = True
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)


class GoogleConfig(BaseModel):
    """Google tools settings."""

    calendar_id: str = "primary"


class MemberConfig(BaseModel):
    """Configuration for a single team member."""

    name: str
    role: str = ""
    tools: list[str] = Field(default_factory=list)
    model_provider: str = ""   # "" = inherit main model
    model_id: str = ""         # "" = inherit main model
    instructions: list[str] = Field(default_factory=list)
    instructions_file: str = ""  # path to .md file loaded at runtime


class DeepWorkConfig(BaseModel):
    """Deep work — autonomous background execution settings."""

    enabled: bool = False
    background: bool = True              # False = blocking
    activation: str = "suggest"          # "suggest" | "explicit" | "auto"
    max_iterations: int = 50
    max_time_minutes: int = 240          # 4 hours
    progress_interval_minutes: int = 5
    progress_channel: str = ""           # "" = originating channel
    save_results_to_workspace: bool = True


class TeamConfig(BaseModel):
    """Agent Team settings (enabled by default with Vandelay Expert)."""

    enabled: bool = True
    mode: str = "coordinate"  # coordinate | route | broadcast | tasks
    members: list[str | MemberConfig] = Field(
        default_factory=lambda: ["vandelay-expert"],
    )


# Maps (nested_key_tuple) -> env_var_name for secret fields.
# Used by the migration and env-loading logic in settings.py.
SECRET_FIELD_ENV_MAP: dict[tuple[str, ...], str] = {
    ("channels", "telegram_bot_token"): "TELEGRAM_TOKEN",
    ("channels", "whatsapp_access_token"): "WHATSAPP_ACCESS_TOKEN",
    ("channels", "whatsapp_verify_token"): "WHATSAPP_VERIFY_TOKEN",
    ("channels", "whatsapp_app_secret"): "WHATSAPP_APP_SECRET",
    ("server", "secret_key"): "VANDELAY_SECRET_KEY",
    ("knowledge", "embedder", "api_key"): "VANDELAY_EMBEDDER_API_KEY",
}
