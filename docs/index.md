# Vandelay

**An always-on AI agent platform built on [Agno](https://github.com/agno-agi/agno).**

Vandelay gives you a self-hosted AI agent that runs 24/7 — with memory, tools, scheduling, and multi-channel access out of the box.

---

## Why Vandelay?

- **Always on** — Runs as a daemon with heartbeat, cron jobs, and proactive scheduling
- **Self-hosted first** — Your data stays on your server. No cloud lock-in.
- **Multi-channel** — Terminal, Telegram, WhatsApp, WebSocket — same agent, shared memory
- **Team mode** — Supervisor delegates to specialist agents with scoped tools
- **Extensible** — 100+ tools from Agno's ecosystem, plus custom tool authoring
- **CLI-first** — One command to install, onboard, and start

## Quick Install

```bash
uv tool install vandelay
vandelay onboard
vandelay start
```

## What's Inside

| Feature | Description |
|---------|-------------|
| [Agent Teams](concepts/teams.md) | Supervisor + specialist agents with tool-scoped delegation |
| [Memory](concepts/memory.md) | Session history, agentic memory, workspace files |
| [Knowledge/RAG](concepts/knowledge.md) | Document ingestion, vector search, embedder auto-resolution |
| [Scheduling](guides/scheduling.md) | Cron jobs, heartbeat, active hours |
| [Channels](concepts/channels.md) | Terminal, Telegram, WhatsApp, WebSocket |
| [Safety](concepts/safety.md) | Trust/confirm/tiered modes, blocked patterns, sandboxing |
| [Browser Control](tools/built-in.md) | Anti-detect Firefox via Camoufox |
| [Deployment](deployment/index.md) | systemd daemon, VPS guides, security hardening |

## Get Started

Ready to go? Head to the [Getting Started](getting-started/index.md) guide.
