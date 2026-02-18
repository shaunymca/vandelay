# Concepts

This section explains how Vandelay works under the hood. Read these to understand the "why" behind the platform.

## Core Concepts

| Concept | What It Covers |
|---------|---------------|
| [Architecture](architecture.md) | System diagram, request flow, component overview |
| [Agents](agents.md) | Agent lifecycle, workspace files, system prompt assembly |
| [Teams](teams.md) | Supervisor model, specialist delegation, team modes |
| [Memory](memory.md) | Session history, agentic memory, workspace files, DB storage |
| [Knowledge](knowledge.md) | RAG pipeline, embedders, vector store, document ingestion |
| [Channels](channels.md) | Channel-agnostic design, Terminal/Telegram/WhatsApp/WebSocket |
| [Safety](safety.md) | Safety modes, blocked patterns, sandboxing |

## How They Fit Together

```
Channels → ChatService → Agent/Team → Tools
                ↕              ↕
            Sessions      Memory + Knowledge
                ↕
            SQLite DB
```

Messages arrive from any channel, get processed by the agent (or team supervisor), which uses tools, memory, and knowledge to respond. Everything persists through the unified SQLite database.
