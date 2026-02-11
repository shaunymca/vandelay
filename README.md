<div align="center">

```
╦  ╦╔═╗╔╗╔╔╦╗╔═╗╦  ╔═╗╦ ╦
╚╗╔╝╠═╣║║║ ║║║╣ ║  ╠═╣╚╦╝
 ╚╝ ╩ ╩╝╚╝═╩╝╚═╝╩═╝╩ ╩ ╩
```

### *The employee who doesn't exist.*

An always-on AI agent that works so you don't have to.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-279%20passed-brightgreen.svg)]()
[![Powered by Agno](https://img.shields.io/badge/powered%20by-Agno-red.svg)](https://github.com/agno-agi/agno)

[Features](#-features) &bull; [Get Started](#-get-started) &bull; [CLI Reference](#-cli-reference) &bull; [How-To Guide](#-how-to-guide) &bull; [Deploy](#-deploy)

</div>

---

## What is Vandelay?

Vandelay is an always-on AI agent built on [Agno](https://github.com/agno-agi/agno) — the framework that handles models, memory, tools, and teams so you don't have to wire them yourself.

Agno ships with **70+ prebuilt tool integrations** (search, email, Slack, GitHub, databases, browsers, and more). Vandelay wraps all of that into a single CLI — one command to set up, one command to add any tool. Connect it to [AgentOS](https://os.agno.com) and you get a full management UI with chat, session history, memory, knowledge search, and token monitoring out of the box.

Add Telegram, WhatsApp, shell access with safety guardrails, scheduled tasks, and a daemon service — and you have a personal AI agent that runs 24/7 on your own infrastructure.

---

## &#x2728; Features

| | Feature | Description |
|---|---|---|
| &#x1f680; | **One-Click Setup** | Interactive CLI wizard — model, auth, tools, channels in 60 seconds |
| &#x1f9f0; | **70+ Tools** | `vandelay tools add duckduckgo` — search, file, shell, email, slack, and more |
| &#x1f9e0; | **Persistent Memory** | SQLite or Postgres-backed memory that survives restarts |
| &#x1f4ac; | **Multi-Channel** | Terminal chat, Telegram bot, WhatsApp — same agent, same memory |
| &#x1f310; | **Browser Control** | Crawl4ai for scraping, Camofox for stealth browsing with accessibility snapshots |
| &#x1f6e1;&#xfe0f; | **Shell Safety** | Three modes: Trust, Confirm, Tiered — destructive commands always blocked |
| &#x26a1; | **AgentOS Ready** | Connect to [os.agno.com](https://os.agno.com) for chat, sessions, memory, and knowledge UI |
| &#x1f4da; | **Knowledge / RAG** | Add docs, PDFs, code — vector-searched and injected into agent context |
| &#x1f552; | **Scheduler + Cron** | Natural-language cron jobs, heartbeat monitoring, APScheduler engine |
| &#x1f3d7;&#xfe0f; | **Agent Teams** | Opt-in supervisor with browser, system, scheduler, and knowledge specialists |
| &#x1f504; | **Self-Restart** | `--watch` flag auto-restarts on file changes (src, config, workspace) |
| &#x1f4e6; | **Daemon Service** | `vandelay daemon install` — systemd (Linux) or launchd (macOS) service |

---

## &#x1f680; Get Started

### Prerequisites

- **Python 3.11+** — [download](https://www.python.org/downloads/)
- **[uv](https://docs.astral.sh/uv/)** — `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`)
- **An API key** from [Anthropic](https://console.anthropic.com/), [OpenAI](https://platform.openai.com/), [Google](https://aistudio.google.com/), [OpenRouter](https://openrouter.ai/), or a local [Ollama](https://ollama.com/) install

### Install & run

```bash
# 1. Clone and install
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync

# 2. Run the setup wizard (model, API key, safety mode, tools, channels)
uv run vandelay onboard

# 3. Launch the agent
uv run vandelay start
```

The onboard wizard walks you through 8 steps — identity, model, auth, safety mode, browser tools, workspace, messaging channels, and knowledge base. Config is saved to `~/.vandelay/config.json` and can be changed anytime with `/config` in chat.

After `vandelay start`, you get:
- **Terminal chat** — talk to your agent directly in the console
- **FastAPI server** at `http://localhost:8000` — REST API and AgentOS-compatible endpoint
- **WebSocket** at `/ws/terminal` — real-time streaming chat
- **Webhooks** for Telegram and WhatsApp (if configured)
- **AgentOS** — connect at [os.agno.com](https://os.agno.com) for a full web UI with chat, sessions, memory, and knowledge

### Verify it works

```bash
# Check health
curl http://localhost:8000/health

# Run tests
uv run pytest tests/ -v
```

---

## &#x1f3d7;&#xfe0f; Architecture

Each layer is a sealed compartment — memory, tools, and channels operate independently so a failure in one never floods the others.

```
                ┌──────────────────────────────────────────────┐
                │               Vandelay Agent Core            │
                │          (single agent or team mode)         │
                │                                              │
                │   ┌──────────┐  ┌────────┐  ┌───────────┐   │
                │   │  Memory  │  │ Tools  │  │ Knowledge │   │
                │   │ (SQLite/ │  │ (70+)  │  │ (RAG /    │   │
                │   │ Postgres)│  │        │  │  LanceDB) │   │
                │   └──────────┘  └────────┘  └───────────┘   │
                │                                              │
                │   ┌──────────┐  ┌────────────────────────┐   │
                │   │Scheduler │  │ File Watcher           │   │
                │   │(APSched) │  │ (auto-restart on edit) │   │
                │   └──────────┘  └────────────────────────┘   │
                │                                              │
                └───────────────────┬──────────────────────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
              ┌──────▼──────┐ ┌────▼────┐ ┌───────▼──────┐
              │  Terminal   │ │FastAPI  │ │  Channels    │
              │  Chat (CLI) │ │+ WS API │ │ TG / WA      │
              └─────────────┘ └─────────┘ └──────────────┘
```

---

## &#x1f4cb; CLI Reference

### Top-Level Commands

| Command | Description |
|---------|-------------|
| `vandelay onboard` | Interactive setup wizard (8 steps) |
| `vandelay onboard -n` | Headless onboarding from environment variables |
| `vandelay start` | Launch agent + API server + terminal chat |
| `vandelay start --server` | Server-only mode (headless / daemon) |
| `vandelay start --watch` | Auto-restart on file changes |
| `vandelay status` | Show config, channels, server info |
| `vandelay --version` | Print version and banner |

### Tool Management

| Command | Description |
|---------|-------------|
| `vandelay tools list` | Show all 70+ available Agno tools |
| `vandelay tools list --enabled` | Show only enabled tools |
| `vandelay tools list --category search` | Filter by category |
| `vandelay tools add <name>` | Enable a tool + install its deps |
| `vandelay tools remove <name>` | Disable a tool |
| `vandelay tools info <name>` | Show tool details |
| `vandelay tools refresh` | Rescan Agno for new tools |

### Cron Jobs

| Command | Description |
|---------|-------------|
| `vandelay cron list` | Show all scheduled jobs |
| `vandelay cron add <name> <expr> <cmd>` | Add a cron job (e.g. `"*/5 * * * *"`) |
| `vandelay cron remove <id>` | Delete a job permanently |
| `vandelay cron pause <id>` | Pause a job without deleting |
| `vandelay cron resume <id>` | Resume a paused job |

### Knowledge / RAG

| Command | Description |
|---------|-------------|
| `vandelay knowledge add <path>` | Index a file or directory |
| `vandelay knowledge list` | Show indexed documents |
| `vandelay knowledge clear` | Remove all indexed documents |
| `vandelay knowledge status` | Show knowledge config and stats |

### Daemon Service

| Command | Description |
|---------|-------------|
| `vandelay daemon install` | Install as systemd (Linux) or launchd (macOS) service |
| `vandelay daemon uninstall` | Remove the service |
| `vandelay daemon start` | Start the service |
| `vandelay daemon stop` | Stop the service |
| `vandelay daemon restart` | Restart the service |
| `vandelay daemon status` | Show service status |
| `vandelay daemon logs` | Tail service logs |

### In-Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Current config + server info |
| `/config` | Change settings on the fly |
| `/new` | Start a new chat session |
| `/quit` | Exit gracefully |

---

## &#x1f4d6; How-To Guide

<details>
<summary><strong>1. Extra Model Providers</strong></summary>

The base install includes all providers. If you only want specific ones:

```bash
uv sync --extra anthropic    # Claude
uv sync --extra openai       # GPT
uv sync --extra google       # Gemini
uv sync --extra all          # All providers
```

</details>

<details>
<summary><strong>2. Onboarding Walkthrough</strong></summary>

```bash
uv run vandelay onboard
```

Before we go any further — here's exactly what the onboarding does, so there are no surprises. The wizard guides you through **8 steps**:

1. **Identity** — Name your agent (default: "Claw") and set your user ID
2. **AI Model** — Pick provider (Anthropic/OpenAI/Google/Ollama/OpenRouter) and model
3. **Safety Mode** — Confirm, Tiered, or Trust for shell commands
4. **Timezone** — Auto-detected or manually selected
5. **Browser Tools** — Crawl4ai (recommended) and/or Camofox (experimental)
6. **Workspace** — Initializes `~/.vandelay/workspace/` with personality templates
7. **Channels** — Telegram and/or WhatsApp (optional)
8. **Knowledge Base** — Enable document search / RAG (optional)

On Linux and macOS, you'll also be offered the option to install Vandelay as a system service.

Config is saved to `~/.vandelay/config.json`. You can change anything later with `/config` in chat or by editing the file directly.

</details>

<details>
<summary><strong>3. Managing Tools</strong></summary>

Vandelay auto-discovers every toolkit in the Agno package — search, file management, email, Slack, GitHub, databases, and more. Don't install what you don't need; you can't lose what you never added.

```bash
# See everything available
vandelay tools list

# Filter by category
vandelay tools list --category search
vandelay tools list --category communication

# Enable a tool (auto-installs pip deps)
vandelay tools add duckduckgo
vandelay tools add slack

# Disable
vandelay tools remove slack

# Get details
vandelay tools info shell
```

After adding or removing tools, restart your agent for changes to take effect.

</details>

<details>
<summary><strong>4. Telegram Setup</strong></summary>

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot and copy the token
3. Either run `vandelay onboard` and select Telegram, or:

```bash
# Set in ~/.vandelay/.env
TELEGRAM_TOKEN=your-token-here
TELEGRAM_CHAT_ID=your-chat-id       # optional — locks to one chat
```

4. Start the agent: `vandelay start`
5. Message your bot — it shares the same agent, memory, and tools as terminal chat

</details>

<details>
<summary><strong>5. WhatsApp Setup</strong></summary>

Requires a [Meta Business App](https://developers.facebook.com/) with WhatsApp Cloud API access.

1. Set up a Meta App with WhatsApp product
2. Get your access token, phone number ID, and app secret
3. Configure during `vandelay onboard` or set in `~/.vandelay/.env`:

```bash
WHATSAPP_ACCESS_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_VERIFY_TOKEN=vandelay-verify    # for webhook validation
WHATSAPP_APP_SECRET=your-secret          # optional, for signature verification
```

4. Point your Meta webhook to `https://your-server:8000/webhooks/whatsapp`

</details>

<details>
<summary><strong>6. Browser Tools (Crawl4ai + Camofox)</strong></summary>

### Crawl4ai (Recommended)
Free, fast web crawling with JavaScript rendering.

```bash
vandelay tools add crawl4ai
uv add crawl4ai
```

### Camofox (Experimental)
Anti-detection browser built on Firefox with accessibility tree snapshots — lets the agent "see" and interact with pages like a human.

```bash
vandelay tools add camofox
```

Camofox automatically installs a sandboxed Node.js environment and the Camoufox browser. No system-wide installs needed.

Enable both during onboarding or via `vandelay tools add`.

</details>

<details>
<summary><strong>7. Safety Modes Explained</strong></summary>

Controls how shell commands are executed:

| Mode | Behavior |
|------|----------|
| **Confirm** | Every command requires your explicit approval (default) |
| **Tiered** | Safe commands (ls, cat, echo) run freely; risky ones need approval |
| **Trust** | All commands execute immediately (use on trusted servers only) |

Obviously, some things should never run. **Always blocked** regardless of mode: `rm -rf /`, `mkfs`, `dd if=`, `:(){`, and other destructive patterns.

Change your safety mode anytime with `/config` in chat.

</details>

<details>
<summary><strong>8. Cron Jobs & Scheduling</strong></summary>

Schedule recurring tasks using standard cron expressions. Jobs are saved to `~/.vandelay/cron_jobs.json` and executed by the APScheduler engine.

```bash
# Add a job — runs every 30 minutes
vandelay cron add "Check emails" "*/30 * * * *" "Check my inbox and summarize new messages"

# Daily standup at 9am UTC
vandelay cron add "Standup" "0 9 * * *" "Prepare a standup summary of yesterday's work" --tz UTC

# List all jobs
vandelay cron list

# Pause / resume / remove
vandelay cron pause <job-id>
vandelay cron resume <job-id>
vandelay cron remove <job-id>
```

You can also ask your agent to schedule jobs via natural language in chat — the agent has built-in scheduler tools.

</details>

<details>
<summary><strong>9. Knowledge / RAG</strong></summary>

Give your agent access to your documents. Vandelay uses LanceDB for vector storage and supports OpenAI, Google, or Ollama embedders.

```bash
# Enable knowledge during onboarding, or toggle with /config

# Add a file or directory
vandelay knowledge add ~/docs/project-spec.pdf
vandelay knowledge add ~/repos/my-project/

# Check what's indexed
vandelay knowledge list
vandelay knowledge status

# Clear everything
vandelay knowledge clear
```

Supported file types: `.txt`, `.md`, `.pdf`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.toml`, `.csv`, `.html`, `.xml`, and more.

The embedder is auto-selected based on your model provider. Anthropic has no embedding API, so it falls back to OpenAI if `OPENAI_API_KEY` is available.

</details>

<details>
<summary><strong>10. Agent Teams (Supervisor Mode)</strong></summary>

Enable team mode to split work across specialist agents. The supervisor routes tasks to the right specialist based on intent.

| Specialist | Handles |
|-----------|---------|
| **browser** | Web browsing, scraping, screenshots |
| **system** | Shell commands, file operations |
| **scheduler** | Cron jobs, reminders, recurring tasks |
| **knowledge** | Document search, RAG queries |

Toggle team mode with `/config` in chat, or set it in `~/.vandelay/config.json`:

```json
{
  "team": {
    "enabled": true,
    "members": ["browser", "system", "scheduler", "knowledge"]
  }
}
```

When disabled (default), the main agent handles everything with all tools. Team mode is better for complex multi-step workflows.

</details>

<details>
<summary><strong>11. Daemon Service</strong></summary>

Run Vandelay as a persistent system service that starts on boot and auto-restarts on failure.

```bash
# Install the service (Linux systemd or macOS launchd)
vandelay daemon install

# Manage it
vandelay daemon start
vandelay daemon stop
vandelay daemon restart
vandelay daemon status
vandelay daemon logs

# Remove the service
vandelay daemon uninstall
```

On Linux, this creates a user-level systemd unit at `~/.config/systemd/user/vandelay.service`. On macOS, it creates a LaunchAgent at `~/Library/LaunchAgents/com.vandelay.agent.plist`. No sudo required.

</details>

<details>
<summary><strong>12. Self-Restart (File Watcher)</strong></summary>

Use the `--watch` flag to auto-restart when source files, config, or workspace templates change:

```bash
vandelay start --watch
vandelay start --server --watch
```

The watcher monitors `.py`, `.json`, `.md`, `.toml`, and `.env` files in `src/`, `~/.vandelay/config.json`, and `~/.vandelay/workspace/`. Changes trigger a graceful restart with a 1-second debounce.

</details>

<details>
<summary><strong>13. AgentOS (Web Control Panel)</strong></summary>

[AgentOS](https://docs.agno.com/agent-os/connect-your-os) is Agno's hosted control panel at [os.agno.com](https://os.agno.com). It connects directly to your running Vandelay server from the browser — no data is routed through Agno's servers.

### Setup

1. Start your agent: `vandelay start` (or `vandelay start --server`)
2. Go to [os.agno.com](https://os.agno.com) and sign in
3. Click **Add new OS**
4. Fill in:
   - **Environment** — Local Development or Production
   - **Endpoint URL** — where your server is running (e.g. `http://localhost:8000`)
   - **OS Name** — a label for this instance (e.g. "Vandelay Local")
   - **Tags** — optional
5. Click **CONNECT**

The dashboard shows a **Running** status and gives you access to:

| Feature | Description |
|---------|-------------|
| **Chat** | Web-based chat with streaming responses |
| **Sessions** | Browse and resume past conversations |
| **Memory** | View what your agent remembers across sessions |
| **Knowledge** | See indexed documents and RAG sources |

> **Note:** For remote deployments, your endpoint must be reachable from your browser. If using Tailscale, connect from a device on your Tailnet. For public access, use Tailscale Funnel or an nginx proxy with TLS.

### API Endpoints

Vandelay also exposes a REST API directly:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /status` | Agent config and status |
| `WS /ws/terminal` | Real-time WebSocket chat |
| `POST /webhooks/telegram` | Telegram webhook receiver |
| `POST /webhooks/whatsapp` | WhatsApp webhook receiver |

### Server modes

```bash
# Terminal chat + server (default)
vandelay start

# Server only (headless/daemon)
vandelay start --server
```

</details>

<details>
<summary><strong>14. Deployment</strong></summary>

See the full **[Deployment Guide](DEPLOYMENT.md)** for Railway setup, VPS provisioning, Tailscale security, webhook routing, and production hardening.

</details>

<details>
<summary><strong>15. Database (SQLite vs PostgreSQL)</strong></summary>

**Default: SQLite** — zero config, stored at `~/.vandelay/data/vandelay.db`.

**PostgreSQL** — set the `DATABASE_URL` environment variable:

```bash
# In ~/.vandelay/.env
DATABASE_URL=postgresql://user:pass@localhost:5432/vandelay
```

Install the Postgres driver:

```bash
uv sync --extra postgres
```

Both backends store agent memory, session history, and configuration. The investment is zero either way — SQLite ships with Python, and Postgres is a one-line env var swap.

</details>

<details>
<summary><strong>16. Customizing Your Agent (Workspace Templates)</strong></summary>

The workspace at `~/.vandelay/workspace/` contains markdown templates that shape your agent's personality and behavior:

| File | Purpose |
|------|---------|
| `SOUL.md` | Core personality, tone, and values |
| `USER.md` | Info about you — timezone, preferences, context |
| `AGENTS.md` | Team member definitions (for multi-agent setups) |
| `TOOLS.md` | Tool usage guidelines and restrictions |
| `BOOTSTRAP.md` | First-run instructions (auto-removed after first session) |
| `HEARTBEAT.md` | Periodic self-check behavior |
| `MEMORY.md` | Curated long-term memories (updated by the agent) |

Edit these files directly — this is how you master the art of shaping your agent's behavior. Changes take effect on next agent restart.

</details>

<details>
<summary><strong>17. Environment Variables Reference</strong></summary>

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `GOOGLE_API_KEY` | Google AI API key | — |
| `TELEGRAM_TOKEN` | Telegram bot token | — |
| `TELEGRAM_CHAT_ID` | Lock Telegram to one chat | — |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Cloud API token | — |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | — |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | `vandelay-verify` |
| `WHATSAPP_APP_SECRET` | Meta app secret (signature verification) | — |
| `VANDELAY_HOST` | Server bind address | `0.0.0.0` |
| `VANDELAY_PORT` | Server port | `8000` |
| `VANDELAY_SECRET_KEY` | JWT signing key | — |
| `VANDELAY_AUTO_RESTART` | Enable file-watcher auto-restart | `0` |
| `VANDELAY_AUTO_ONBOARD` | Auto-onboard on first `start` | `0` |
| `DATABASE_URL` | PostgreSQL connection string | SQLite |

All `VANDELAY_*` variables override settings from `~/.vandelay/config.json`.

</details>

---

## &#x1f682; Deploy

See the **[Deployment Guide](DEPLOYMENT.md)** for Railway, VPS, Tailscale, and webhook setup.

| Path | Best For | Guide Section |
|------|----------|---------------|
| **Railway** | Quick setup, no server management | [Railway guide](DEPLOYMENT.md#deploy-to-railway) |
| **VPS + Tailscale** | Full control, network isolation | [VPS guide](DEPLOYMENT.md#deploy-to-a-vps) |

---

## &#x1f4dc; License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built with [Agno](https://github.com/agno-agi/agno)

</div>
