"""Paths and default values used across the project."""

from pathlib import Path

# Base directory for all vandelay data
VANDELAY_HOME = Path.home() / ".vandelay"

# Sub-directories
CONFIG_DIR = VANDELAY_HOME
CONFIG_FILE = CONFIG_DIR / "config.json"
WORKSPACE_DIR = VANDELAY_HOME / "workspace"
DB_DIR = VANDELAY_HOME / "data"
BROWSER_PROFILE_DIR = VANDELAY_HOME / "browser_profile"
KNOWLEDGE_DIR = WORKSPACE_DIR / "knowledge"
LOGS_DIR = VANDELAY_HOME / "logs"
CRON_FILE = VANDELAY_HOME / "cron_jobs.json"
TASK_QUEUE_FILE = VANDELAY_HOME / "task_queue.json"
TOOL_REGISTRY_FILE = VANDELAY_HOME / "tool_registry.json"
MEMBERS_DIR = VANDELAY_HOME / "members"
THREADS_FILE = VANDELAY_HOME / "threads.json"
CUSTOM_TOOLS_DIR = VANDELAY_HOME / "custom_tools"
CORPUS_VERSIONS_FILE = VANDELAY_HOME / "data" / "corpus_versions.json"

# Database defaults
DEFAULT_DB_FILE = DB_DIR / "vandelay.db"

# Server defaults
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# Heartbeat
DEFAULT_HEARTBEAT_INTERVAL_MINUTES = 30

# Safety modes
SAFETY_TRUST = "trust"
SAFETY_CONFIRM = "confirm"
SAFETY_TIERED = "tiered"

# Supported model providers
MODEL_PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "env_key": "ANTHROPIC_API_KEY",
        "token_env_key": None,
        "default_model": "claude-sonnet-4-5-20250929",
        "token_label": None,
        "token_help": None,
        "api_key_label": "Anthropic API key",
        "api_key_help": "Get your API key from console.anthropic.com/settings/keys",
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "env_key": "OPENAI_API_KEY",
        "token_env_key": "OPENAI_AUTH_TOKEN",
        "default_model": "gpt-4o",
        "token_label": "OpenAI token (paste session token)",
        "token_help": (
            "Use the API key from your ChatGPT Plus/Pro subscription"
            " at platform.openai.com/api-keys"
        ),
        "api_key_label": "OpenAI API key",
        "api_key_help": "Get your API key from platform.openai.com/api-keys",
    },
    "google": {
        "name": "Google (Gemini)",
        "env_key": "GOOGLE_API_KEY",
        "token_env_key": None,
        "default_model": "gemini-2.0-flash",
        "token_label": None,
        "token_help": None,
        "api_key_label": "Google API key",
        "api_key_help": "Get your API key from aistudio.google.com/apikey",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "env_key": None,
        "token_env_key": None,
        "default_model": "llama3.1",
        "token_label": None,
        "token_help": None,
        "api_key_label": None,
        "api_key_help": None,
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "token_env_key": None,
        "default_model": "anthropic/claude-sonnet-4-5-20250929",
        "token_label": None,
        "token_help": None,
        "api_key_label": "OpenRouter API key",
        "api_key_help": "Get your API key from openrouter.ai/keys",
    },
}
