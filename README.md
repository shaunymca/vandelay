<div align="center">

# VANDELAY

### *The employee who doesn't exist.*

An always-on AI agent that works so you don't have to.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-844%20passed-brightgreen.svg)]()
[![Powered by Agno](https://img.shields.io/badge/powered%20by-Agno-red.svg)](https://github.com/agno-agi/agno)

**[Documentation](https://shaunymca.github.io/vandelay/)** &bull; [Get Started](#get-started) &bull; [Features](#features)

</div>

---

## What is Vandelay?

Vandelay is a self-hosted AI agent built on [Agno](https://github.com/agno-agi/agno) that runs 24/7 with memory, tools, scheduling, and multi-channel access out of the box.

You get a personal agent that:
- Remembers everything across sessions (SQLite-backed memory)
- Has 100+ tool integrations ready to enable (search, email, GitHub, databases, browser, and more)
- Runs scheduled tasks and monitors itself via heartbeat
- Connects over Terminal, Telegram, WhatsApp, and WebSocket
- Supports agent teams with a built-in Vandelay Expert specialist

One command to install, one to run.

---

## Features

| Feature | Description |
|---------|-------------|
| **100+ Tools** | Enable any tool with `vandelay tools enable <slug>` |
| **Persistent Memory** | SQLite-backed memory and session history that survives restarts |
| **Multi-Channel** | Terminal, Telegram, WhatsApp, WebSocket - same agent, shared memory |
| **Knowledge / RAG** | Add docs, PDFs, code - vector-searched and injected into context |
| **Scheduler + Cron** | Natural-language cron jobs, heartbeat, active hours |
| **Agent Teams** | Supervisor with specialist delegation and scoped tools |
| **Browser Control** | Anti-detect Firefox via Camoufox for web automation |
| **Shell Safety** | Trust / Confirm / Tiered modes, destructive commands always blocked |
| **Daemon Service** | `vandelay daemon install` - systemd (Linux) or launchd (macOS) |
| **Self-Hosted First** | Your data stays on your server. No cloud lock-in. |

---

## Get Started

```bash
# Install from source
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync
uv tool install -e .

# Open the TUI dashboard (onboarding runs automatically on first launch)
vandelay

# Start the agent server (in a separate terminal, or install the daemon)
vandelay start
```

For a full walkthrough including prerequisites, configuration, and deployment, see the **[documentation site](https://shaunymca.github.io/vandelay/)**.

---

## Documentation

| Section | Description |
|---------|-------------|
| [Getting Started](https://shaunymca.github.io/vandelay/getting-started/) | Installation, quickstart, first message in under 5 minutes |
| [Concepts](https://shaunymca.github.io/vandelay/concepts/architecture/) | Architecture, agents, teams, memory, knowledge, channels, safety |
| [Guides](https://shaunymca.github.io/vandelay/guides/) | Teams, custom tools, Telegram, Google services, scheduling, templates |
| [Tools](https://shaunymca.github.io/vandelay/tools/) | 100+ tool catalog grouped by category, built-in toolkits |
| [CLI Reference](https://shaunymca.github.io/vandelay/cli/) | Every command documented with examples |
| [Configuration](https://shaunymca.github.io/vandelay/configuration/) | Full config schema, env vars, examples |
| [Deployment](https://shaunymca.github.io/vandelay/deployment/) | VPS setup, systemd daemon, security hardening, troubleshooting |

---

## Built on Agno

Vandelay is built on [Agno](https://github.com/agno-agi/agno), an open-source framework for building multi-modal agents with memory, tools, and team support. Agno handles the model layer, tool integrations, memory backends, and team coordination — Vandelay wraps it into a ready-to-deploy platform.

---

## License

MIT - see [LICENSE](LICENSE)
