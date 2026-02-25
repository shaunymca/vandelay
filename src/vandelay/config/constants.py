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

# Common IANA timezones — used by TUI Select widgets and CLI prompts.
# Format: (display_label, iana_value)
COMMON_TIMEZONES: list[tuple[str, str]] = [
    ("UTC", "UTC"),
    # Americas
    ("America/New_York (ET)", "America/New_York"),
    ("America/Chicago (CT)", "America/Chicago"),
    ("America/Denver (MT)", "America/Denver"),
    ("America/Los_Angeles (PT)", "America/Los_Angeles"),
    ("America/Anchorage (AK)", "America/Anchorage"),
    ("Pacific/Honolulu (HI)", "Pacific/Honolulu"),
    ("America/Toronto", "America/Toronto"),
    ("America/Vancouver", "America/Vancouver"),
    ("America/Sao_Paulo", "America/Sao_Paulo"),
    ("America/Argentina/Buenos_Aires", "America/Argentina/Buenos_Aires"),
    ("America/Mexico_City", "America/Mexico_City"),
    # Europe
    ("Europe/London (GMT/BST)", "Europe/London"),
    ("Europe/Dublin", "Europe/Dublin"),
    ("Europe/Lisbon", "Europe/Lisbon"),
    ("Europe/Paris (CET)", "Europe/Paris"),
    ("Europe/Berlin", "Europe/Berlin"),
    ("Europe/Amsterdam", "Europe/Amsterdam"),
    ("Europe/Madrid", "Europe/Madrid"),
    ("Europe/Rome", "Europe/Rome"),
    ("Europe/Stockholm", "Europe/Stockholm"),
    ("Europe/Warsaw", "Europe/Warsaw"),
    ("Europe/Helsinki", "Europe/Helsinki"),
    ("Europe/Athens", "Europe/Athens"),
    ("Europe/Moscow", "Europe/Moscow"),
    # Africa / Middle East
    ("Africa/Cairo", "Africa/Cairo"),
    ("Africa/Johannesburg", "Africa/Johannesburg"),
    ("Africa/Lagos", "Africa/Lagos"),
    ("Asia/Dubai", "Asia/Dubai"),
    ("Asia/Riyadh", "Asia/Riyadh"),
    # Asia
    ("Asia/Kolkata (IST)", "Asia/Kolkata"),
    ("Asia/Karachi", "Asia/Karachi"),
    ("Asia/Dhaka", "Asia/Dhaka"),
    ("Asia/Bangkok", "Asia/Bangkok"),
    ("Asia/Singapore", "Asia/Singapore"),
    ("Asia/Shanghai (CST)", "Asia/Shanghai"),
    ("Asia/Hong_Kong", "Asia/Hong_Kong"),
    ("Asia/Taipei", "Asia/Taipei"),
    ("Asia/Seoul", "Asia/Seoul"),
    ("Asia/Tokyo (JST)", "Asia/Tokyo"),
    # Oceania
    ("Australia/Perth", "Australia/Perth"),
    ("Australia/Adelaide", "Australia/Adelaide"),
    ("Australia/Sydney (AEST)", "Australia/Sydney"),
    ("Australia/Brisbane", "Australia/Brisbane"),
    ("Pacific/Auckland", "Pacific/Auckland"),
]

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
        "token_env_key": None,
        "default_model": "gpt-4o",
        "token_label": "ChatGPT Plus/Pro subscription (Codex OAuth)",
        "token_help": "Run `npm install -g @openai/codex && codex login` first.",
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
    "groq": {
        "name": "Groq (fast inference)",
        "env_key": "GROQ_API_KEY",
        "token_env_key": None,
        "default_model": "llama-3.3-70b-versatile",
        "token_label": None,
        "token_help": None,
        "api_key_label": "Groq API key",
        "api_key_help": "Get your API key from console.groq.com/keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "token_env_key": None,
        "default_model": "deepseek-chat",
        "token_label": None,
        "token_help": None,
        "api_key_label": "DeepSeek API key",
        "api_key_help": "Get your API key from platform.deepseek.com/api_keys",
    },
    "mistral": {
        "name": "Mistral",
        "env_key": "MISTRAL_API_KEY",
        "token_env_key": None,
        "default_model": "mistral-large-latest",
        "token_label": None,
        "token_help": None,
        "api_key_label": "Mistral API key",
        "api_key_help": "Get your API key from console.mistral.ai/api-keys",
    },
    "together": {
        "name": "Together (open source)",
        "env_key": "TOGETHER_API_KEY",
        "token_env_key": None,
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
        "token_label": None,
        "token_help": None,
        "api_key_label": "Together API key",
        "api_key_help": "Get your API key from api.together.xyz/settings/api-keys",
    },
    "xai": {
        "name": "xAI (Grok)",
        "env_key": "XAI_API_KEY",
        "token_env_key": None,
        "default_model": "grok-2",
        "token_label": None,
        "token_help": None,
        "api_key_label": "xAI API key",
        "api_key_help": "Get your API key from console.x.ai",
    },
    "openrouter": {
        "name": "OpenRouter (multi-provider gateway)",
        "env_key": "OPENROUTER_API_KEY",
        "token_env_key": None,
        "default_model": "anthropic/claude-sonnet-4-5-20250929",
        "token_label": None,
        "token_help": None,
        "api_key_label": "OpenRouter API key",
        "api_key_help": "Get your API key from openrouter.ai/keys",
    },
}
