"""Pydantic models for configuration sub-sections."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
        ]
    )
    command_timeout_seconds: int = 120


class ChannelConfig(BaseModel):
    """Messaging channel settings."""

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    whatsapp_enabled: bool = False
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""


class HeartbeatConfig(BaseModel):
    """Heartbeat / proactive wake settings."""

    enabled: bool = False
    interval_minutes: int = 30
    active_hours_start: int = 8   # 24h format
    active_hours_end: int = 22
    timezone: str = "UTC"


class ServerConfig(BaseModel):
    """HTTP server settings."""

    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = "change-me-to-a-random-string"


class EmbedderConfig(BaseModel):
    """Explicit embedder override. When empty, auto-matches model provider."""

    provider: str = ""  # openai | google | ollama | "" (auto)
    model: str = ""  # e.g. "text-embedding-3-small"
    api_key: str = ""  # only if different from model provider
    base_url: str = ""  # custom endpoint


class KnowledgeConfig(BaseModel):
    """Knowledge/RAG settings."""

    enabled: bool = False
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
