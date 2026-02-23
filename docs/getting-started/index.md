# Getting Started

Welcome to Vandelay. This section gets you from zero to a running agent in under 5 minutes.

## What is Vandelay?

Vandelay is an always-on AI agent platform built on [Agno](https://github.com/agno-agi/agno). It wraps Agno's agent framework with:

- A **TUI dashboard** — the primary interface for chat, config, agents, scheduler, and live status
- A CLI for headless configuration and management
- A FastAPI server for multi-channel access
- A daemon for 24/7 operation with heartbeat and cron scheduling
- Team mode for multi-agent coordination
- Built-in tools for shell, file, browser, and more

## How It Works

```
You (Terminal / Telegram / WhatsApp / WebSocket)
    ↓
FastAPI Server
    ↓
ChatService → Agent (or Team Supervisor)
    ↓                    ↓
Memory / Knowledge    Specialist Members
    ↓                    ↓
SQLite DB            Scoped Tools
```

The agent receives messages from any channel, processes them through Agno's agent framework, and responds, with full access to tools, memory, and knowledge.

## Next Steps

1. **[Installation](installation.md):** Install Vandelay and its dependencies
2. **[Quickstart](quickstart.md):** Send your first message in under 5 minutes
