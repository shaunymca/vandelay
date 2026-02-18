# Architecture

Vandelay is built as a layered system where each component has a clear responsibility.

## System Overview

```
┌─────────────────────────────────────────────────┐
│                   Channels                       │
│  Terminal  │  Telegram  │  WhatsApp  │  WebSocket │
└──────────────────────┬──────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│               FastAPI Server                      │
│  Routes  │  WebSocket Handler  │  Webhook Handler │
└──────────────────────┬───────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│                 ChatService                       │
│  Message routing  │  Channel abstraction          │
└──────────────────────┬───────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│            Agent / Team Supervisor                │
│  Agno Agent  │  Tool dispatch  │  Delegation      │
├──────────────┼────────────────┼──────────────────┤
│   Memory     │   Knowledge    │   Scheduler       │
│  (SQLite)    │  (ChromaDB)   │   (APScheduler)   │
└──────────────────────────────────────────────────┘
```

## Key Components

### ChatService

The central router. All channels send messages through `ChatService.run()`, which resolves the current agent (or team), processes the message, and returns the response. Channel-agnostic by design.

### AgentProvider

A lazy provider protocol that always returns the current agent instance. When config changes trigger a reload (e.g., enabling a tool), the provider creates a new agent without restarting the server.

### Agent Factory

`agents/factory.py` builds agents and teams from config. Handles:

- Model creation from provider settings
- Tool resolution and injection
- Team member creation with scoped tools
- Workspace-based system prompt assembly

### Scheduler Engine

APScheduler-backed cron engine. Jobs are persisted to `cron_jobs.json` and restored on startup. The engine sends cron commands through ChatService as if they were user messages.

### Workspace

Seven markdown files that compose the agent's system prompt:

- `SOUL.md`: Core personality and behavior
- `USER.md`: User preferences and context
- `AGENTS.md`: Team delegation rules
- `TOOLS.md`: Tool usage guidance
- `HEARTBEAT.md`: Proactive task definitions
- `BOOTSTRAP.md`: Startup instructions
- `MEMORY.md`: Persistent notes

## Data Flow

<!-- TODO: Add detailed data flow diagrams -->

## Configuration Hierarchy

Settings resolve in priority order:

1. Environment variables (`VANDELAY_` prefix)
2. `.env` file (`~/.vandelay/.env`)
3. `config.json` (`~/.vandelay/config.json`)
4. Code defaults
