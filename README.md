<div align="center">

```
██╗   ██╗ █████╗ ███╗   ██╗██████╗ ███████╗██╗      █████╗ ██╗   ██╗
██║   ██║██╔══██╗████╗  ██║██╔══██╗██╔════╝██║     ██╔══██╗╚██╗ ██╔╝
██║   ██║███████║██╔██╗ ██║██║  ██║█████╗  ██║     ███████║ ╚████╔╝
╚██╗ ██╔╝██╔══██║██║╚██╗██║██║  ██║██╔══╝  ██║     ██╔══██║  ╚██╔╝
 ╚████╔╝ ██║  ██║██║ ╚████║██████╔╝███████╗███████╗██║  ██║   ██║
  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝
```

### *The employee who doesn't exist.*

An always-on AI agent that works so you don't have to.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-109%20passed-brightgreen.svg)]()
[![Powered by Agno](https://img.shields.io/badge/powered%20by-Agno-red.svg)](https://github.com/agno-agi/agno)

[Quick Start](#-quick-start) &bull; [Features](#-features) &bull; [CLI Reference](#-cli-reference) &bull; [How-To Guide](#-how-to-guide) &bull; [Roadmap](#-roadmap)

</div>

---

## What is Vandelay?

Most agent frameworks ask you to feel your way through a maze of config files, scattered docs, and half-working integrations. We felt that pain too — and found that the real problem wasn't the AI, it was everything around it.

Vandelay is a **deploy-and-forget AI agent platform** built on [Agno](https://github.com/agno-agi/agno). One command to set up. One command to add any of **70+ tools**. Persistent memory across sessions. Telegram, WhatsApp, and terminal access. Browser control. Shell execution with safety guardrails. An always-on agent that handles the work while you handle the rest.

Built from scratch on the Agno framework.

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
| &#x26a1; | **FastAPI + WebSocket** | REST API, AgentOS playground, and real-time WebSocket chat |
| &#x1f3d7;&#xfe0f; | **Agent Teams** | Supervisor architecture ready — champion agents for complex workflows |

---

## &#x1f680; Quick Start

```bash
git clone https://github.com/yourusername/vandelay.git && cd vandelay
uv sync
uv run vandelay onboard
```

That's it. No upfront commitment, no vendor lock-in. The wizard walks you through model selection, API keys, safety mode, browser tools, and messaging channels — then drops you into a live chat session.

---

## &#x1f3d7;&#xfe0f; Architecture

Each layer is a sealed compartment — memory, tools, and channels operate independently so a failure in one never floods the others.

```
                ┌──────────────────────────────────────────────┐
                │               Vandelay Agent Core            │
                │                                              │
                │   ┌──────────┐  ┌────────┐  ┌───────────┐   │
                │   │  Memory  │  │ Tools  │  │ Knowledge │   │
                │   │ (SQLite/ │  │ (70+)  │  │  (RAG)    │   │
                │   │ Postgres)│  │        │  │           │   │
                │   └──────────┘  └────────┘  └───────────┘   │
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
| `vandelay onboard` | Interactive setup wizard (7 steps) |
| `vandelay start` | Launch agent + API server + terminal chat |
| `vandelay start --server` | Server-only mode (headless / daemon) |
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
<summary><strong>1. Prerequisites & Installation</strong></summary>

### Requirements
- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- An API key from Anthropic, OpenAI, Google, or a local Ollama install

### Install

```bash
git clone https://github.com/yourusername/vandelay.git
cd vandelay
uv sync
```

For extra model providers:

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

Before we go any further — here's exactly what the onboarding does, so there are no surprises. The wizard guides you through **7 steps**:

1. **Identity** — Name your agent (default: "Claw")
2. **AI Model** — Pick provider (Anthropic/OpenAI/Google/Ollama) and model
3. **Authentication** — API key or auth token, saved to `~/.vandelay/.env`
4. **Safety Mode** — Confirm, Tiered, or Trust for shell commands
5. **Browser Tools** — Crawl4ai (recommended) and/or Camofox (experimental)
6. **Workspace** — Initializes `~/.vandelay/workspace/` with personality templates
7. **Channels** — Telegram and/or WhatsApp (optional)

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
TELEGRAM_BOT_TOKEN=your-token-here
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
<summary><strong>8. Server & WebSocket API</strong></summary>

### Start the server

```bash
# With terminal chat (default)
vandelay start

# Server only (headless/daemon)
vandelay start --server
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /status` | Agent config and status |
| `GET /docs` | AgentOS interactive playground |
| `WS /ws/terminal` | Real-time WebSocket chat |
| `POST /webhooks/telegram` | Telegram webhook receiver |
| `POST /webhooks/whatsapp` | WhatsApp webhook receiver |

### WebSocket Example

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/terminal");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({ text: "Hello!", session_id: "my-session" }));
```

</details>

<details>
<summary><strong>9. Deploying to a Server (systemd)</strong></summary>

### Quick deploy

```bash
# Copy service file
sudo cp systemd/vandelay.service /etc/systemd/system/vandelay@.service

# Enable and start (replace 'youruser' with your username)
sudo systemctl enable vandelay@youruser
sudo systemctl start vandelay@youruser

# Check logs
journalctl -u vandelay@youruser -f
```

### What the service does
- Runs `vandelay start --server` as a background daemon
- Auto-restarts on failure (10s delay) — it never needs a pep talk
- Reads config from `~/.vandelay/`
- Applies systemd hardening (NoNewPrivileges, ProtectSystem)

### Reverse proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name vandelay.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

</details>

<details>
<summary><strong>10. Database (SQLite vs PostgreSQL)</strong></summary>

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
<summary><strong>11. Customizing Your Agent (Workspace Templates)</strong></summary>

The workspace at `~/.vandelay/workspace/` contains markdown templates that shape your agent's personality and behavior:

| File | Purpose |
|------|---------|
| `SOUL.md` | Core personality, tone, and values |
| `USER.md` | Info about you — timezone, preferences, context |
| `AGENTS.md` | Team member definitions (for multi-agent setups) |
| `TOOLS.md` | Tool usage guidelines and restrictions |
| `BOOTSTRAP.md` | First-run instructions (auto-removed after first session) |
| `HEARTBEAT.md` | Periodic self-check behavior |

Edit these files directly — this is how you master the art of shaping your agent's behavior. Changes take effect on next agent restart.

</details>

<details>
<summary><strong>12. Environment Variables Reference</strong></summary>

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `GOOGLE_API_KEY` | Google AI API key | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `TELEGRAM_CHAT_ID` | Lock Telegram to one chat | — |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Cloud API token | — |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | — |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | `vandelay-verify` |
| `WHATSAPP_APP_SECRET` | Meta app secret (signature verification) | — |
| `VANDELAY_HOST` | Server bind address | `0.0.0.0` |
| `VANDELAY_PORT` | Server port | `8000` |
| `VANDELAY_SECRET_KEY` | JWT signing key | — |
| `DATABASE_URL` | PostgreSQL connection string | SQLite |

All `VANDELAY_*` variables override settings from `~/.vandelay/config.json`.

</details>

---

## &#x1f5fa;&#xfe0f; Roadmap

| Stage | What | Status |
|-------|------|--------|
| 1 | Foundation — config, CLI, basic agent | &#x2705; Complete |
| 2 | FastAPI gateway + WebSocket terminal | &#x2705; Complete |
| 3 | Shell toolkit + safety system | &#x2705; Complete |
| 4 | Telegram + WhatsApp channels | &#x2705; Complete |
| 5 | Browser toolkit (Crawl4ai + Camofox) | &#x2705; Complete |
| 6 | Scheduler, heartbeat, cron jobs | &#x1f6a7; In Progress |
| 7 | Team assembly, knowledge/RAG, self-restart | &#x1f6a7; Planned |

---

## &#x1f91d; Contributing

Contributions welcome — let's build some rapport first. This project is in active development.

1. Fork the repo
2. Create your branch (`git checkout -b feature/amazing-feature`)
3. Install dev deps: `uv sync --group dev`
4. Run tests: `uv run pytest tests/ -v`
5. Run linter: `uv run ruff check src/`
6. Open a PR

---

## &#x1f4dc; License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

*"And you want to be my latex salesman."*

*The best results come when you stop selling and start solving.*

Built with [Agno](https://github.com/agno-agi/agno)

</div>
