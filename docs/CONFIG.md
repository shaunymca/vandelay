# Configuration Reference

Vandelay stores its configuration in `~/.vandelay/config.json`. Settings are loaded with the following priority (highest wins):

1. **Environment variables** (`VANDELAY_` prefix)
2. **`.env` file** (`~/.vandelay/.env`)
3. **config.json** (`~/.vandelay/config.json`)
4. **Defaults** (defined in code)

Generate a default config interactively:

```bash
vandelay onboard
```

---

## Top-Level Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `agent_name` | string | `"Art"` | Display name for the agent |
| `user_id` | string | `""` | Email or identifier — shared across all channels |
| `timezone` | string | `"UTC"` | Timezone for scheduling and heartbeat active hours |
| `db_url` | string | `""` | Database URL. Empty = SQLite at `~/.vandelay/data/vandelay.db`. Set to a `postgresql://` URL for Postgres |
| `workspace_dir` | string | `"~/.vandelay/workspace"` | Directory containing workspace markdown files (SOUL.md, USER.md, etc.) |
| `enabled_tools` | list[string] | `[]` | Tool slugs to load (e.g. `["shell", "file", "python", "tavily"]`) |

---

## `model`

LLM provider and model selection.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `"anthropic"` | Model provider: `anthropic`, `openai`, `google`, `ollama`, `openrouter` |
| `model_id` | string | `"claude-sonnet-4-5-20250929"` | Model identifier passed to the provider |
| `auth_method` | string | `"api_key"` | Authentication method: `api_key` or `token` (OpenAI only) |

---

## `safety`

Shell command safety guardrails.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mode` | string | `"confirm"` | Safety mode: `trust` (auto-approve), `confirm` (ask first), `tiered` (allow safe, confirm risky) |
| `allowed_commands` | list[string] | `["ls", "cat", "head", ...]` | Commands auto-approved in `tiered` mode |
| `blocked_patterns` | list[string] | `["rm -rf /", "mkfs", ...]` | Patterns blocked in all modes |
| `command_timeout_seconds` | int | `120` | Max execution time for shell commands |

---

## `channels`

Messaging channel configuration.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `telegram_enabled` | bool | `false` | Enable the Telegram bot channel |
| `telegram_bot_token` | string | `""` | Telegram bot token (stored in `.env` as `TELEGRAM_TOKEN`) |
| `telegram_chat_id` | string | `""` | Lock Telegram to a single chat ID |
| `whatsapp_enabled` | bool | `false` | Enable the WhatsApp channel |
| `whatsapp_access_token` | string | `""` | WhatsApp Cloud API token (stored in `.env`) |
| `whatsapp_phone_number_id` | string | `""` | WhatsApp phone number ID |
| `whatsapp_verify_token` | string | `""` | Webhook verification token |
| `whatsapp_app_secret` | string | `""` | Meta app secret for signature verification |

---

## `heartbeat`

Proactive wake / heartbeat settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable periodic heartbeat |
| `interval_minutes` | int | `30` | Minutes between heartbeat checks |
| `active_hours_start` | int | `8` | Start of active window (24h format) |
| `active_hours_end` | int | `22` | End of active window (24h format) |
| `timezone` | string | `"UTC"` | Timezone for active hours |

---

## `server`

HTTP server (FastAPI) settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | Bind address |
| `port` | int | `8000` | Listen port |
| `secret_key` | string | `"change-me-to-a-random-string"` | JWT signing key (stored in `.env` as `VANDELAY_SECRET_KEY`) |

---

## `knowledge`

Knowledge / RAG settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable knowledge/RAG pipeline |
| `embedder.provider` | string | `""` | Embedder provider: `openai`, `google`, `ollama`, or `""` (auto-match model provider) |
| `embedder.model` | string | `""` | Embedding model ID (e.g. `"text-embedding-3-small"`) |
| `embedder.api_key` | string | `""` | Embedder API key if different from model provider (stored in `.env`) |
| `embedder.base_url` | string | `""` | Custom embedder endpoint |

Anthropic has no embedding API. When using Anthropic as the model provider, the embedder auto-falls back to OpenAI if `OPENAI_API_KEY` is set.

---

## `google`

Google services settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `calendar_id` | string | `"primary"` | Google Calendar ID to use |

---

## `team`

Agent team (supervisor mode) settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `true` | Enable team mode. When `false`, the main agent handles everything solo |
| `mode` | string | `"coordinate"` | Team mode: `coordinate`, `route`, `broadcast`, `tasks` |
| `members` | list | `["vandelay-expert"]` | Team members — strings (legacy names) or full `MemberConfig` objects |

### Legacy member names

These string shortcuts resolve to preconfigured specialists:

| Name | Tools | Role |
|------|-------|------|
| `browser` | crawl4ai, camofox | Web browsing, scraping, screenshots |
| `system` | shell, file, python | Shell commands, file ops, package management |
| `scheduler` | *(injected)* | Cron jobs, reminders, recurring tasks |
| `knowledge` | *(injected)* | Document search, RAG queries |
| `vandelay-expert` | file, python, shell | Agent builder — designs, creates, tests, and improves team members |

### MemberConfig schema

For full control, use objects instead of strings:

```json
{
  "name": "my-specialist",
  "role": "Description of what this member does",
  "tools": ["shell", "file", "python"],
  "model_provider": "",
  "model_id": "",
  "instructions": ["Extra inline instructions"],
  "instructions_file": "my-specialist.md"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | *(required)* | Unique member identifier |
| `role` | string | `""` | Role description shown to the supervisor |
| `tools` | list[string] | `[]` | Tool slugs this member can use (must be in `enabled_tools`) |
| `model_provider` | string | `""` | Override model provider (empty = inherit main) |
| `model_id` | string | `""` | Override model ID (empty = inherit main) |
| `instructions` | list[string] | `[]` | Inline instruction strings |
| `instructions_file` | string | `""` | Path to `.md` file with instructions (relative to `~/.vandelay/members/`) |

### Template bootstrap

Members whose names match a [starter template](../src/vandelay/agents/templates/) (e.g. `vandelay-expert`, `cto`, `devops`) automatically have their template `.md` copied to `~/.vandelay/members/` on first use. This gives the member rich persona instructions out of the box. The file is yours to edit afterward.

---

## `deep_work`

Autonomous background execution settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable deep work mode |
| `background` | bool | `true` | Run in background (`false` = blocking) |
| `activation` | string | `"suggest"` | Activation mode: `suggest`, `explicit`, `auto` |
| `max_iterations` | int | `50` | Max iterations per deep work session |
| `max_time_minutes` | int | `240` | Max time (minutes) per session |
| `progress_interval_minutes` | int | `5` | Minutes between progress updates |
| `progress_channel` | string | `""` | Channel for progress updates (empty = originating channel) |
| `save_results_to_workspace` | bool | `true` | Save results to workspace files |

---

## Environment Variables

Secret values should be stored in `~/.vandelay/.env`, not in `config.json`. Vandelay automatically migrates any secrets found in config.json to `.env` on startup.

| Variable | Description | Used By |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | model (anthropic) |
| `OPENAI_API_KEY` | OpenAI API key | model (openai), embedder fallback |
| `OPENROUTER_API_KEY` | OpenRouter API key | model (openrouter) |
| `GOOGLE_API_KEY` | Google AI API key | model (google) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Google tools (Gmail, Calendar, etc.) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Google tools |
| `GOOGLE_PROJECT_ID` | Google Cloud project ID | Google tools |
| `TELEGRAM_TOKEN` | Telegram bot token | channels.telegram |
| `TELEGRAM_CHAT_ID` | Lock Telegram to one chat | channels.telegram |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Cloud API token | channels.whatsapp |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | channels.whatsapp |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | channels.whatsapp |
| `WHATSAPP_APP_SECRET` | Meta app secret (signature verification) | channels.whatsapp |
| `VANDELAY_HOST` | Server bind address | server.host |
| `VANDELAY_PORT` | Server port | server.port |
| `VANDELAY_SECRET_KEY` | JWT signing key | server.secret_key |
| `VANDELAY_EMBEDDER_API_KEY` | Embedder API key (if different from model) | knowledge.embedder |
| `VANDELAY_AUTO_RESTART` | Enable file-watcher auto-restart (`1`/`0`) | CLI |
| `VANDELAY_AUTO_ONBOARD` | Auto-onboard on first `start` (`1`/`0`) | CLI |
| `DATABASE_URL` | PostgreSQL connection string (overrides `db_url`) | database |

All `VANDELAY_*` variables override the corresponding settings from `config.json`.

---

## Example Config

A minimal config for team mode with Anthropic and a few tools:

```json
{
  "agent_name": "Art",
  "user_id": "you@example.com",
  "timezone": "America/New_York",
  "enabled_tools": ["shell", "file", "python", "tavily", "camofox"],
  "model": {
    "provider": "anthropic",
    "model_id": "claude-sonnet-4-5-20250929"
  },
  "team": {
    "enabled": true,
    "members": ["vandelay-expert"]
  }
}
```

A fuller config adding Telegram, heartbeat, and custom members:

```json
{
  "agent_name": "Art",
  "user_id": "you@example.com",
  "timezone": "Europe/London",
  "enabled_tools": ["shell", "file", "python", "tavily", "gmail", "googlecalendar", "camofox"],
  "model": {
    "provider": "anthropic",
    "model_id": "claude-sonnet-4-5-20250929"
  },
  "safety": {
    "mode": "tiered"
  },
  "channels": {
    "telegram_enabled": true,
    "telegram_chat_id": "123456789"
  },
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 60,
    "active_hours_start": 9,
    "active_hours_end": 21,
    "timezone": "Europe/London"
  },
  "team": {
    "enabled": true,
    "members": [
      "vandelay-expert",
      "browser",
      "system",
      {
        "name": "my-researcher",
        "role": "Deep research specialist",
        "tools": ["tavily", "crawl4ai"],
        "instructions_file": "my-researcher.md"
      }
    ]
  }
}
```
