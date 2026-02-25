# Memory

Vandelay's memory system gives your agent persistent context across conversations, sessions, and restarts.

## Memory Layers

### 1. Session History

Agno stores conversation history per session in the SQLite database. Configured with:

- `num_history_runs=2`: Include the last 2 conversation turns for context
- `max_tool_calls_from_history=5`: Limit tool call results in history to manage tokens
- `enable_session_summaries=True`: Summarize older sessions for long-term context

### 2. Agentic Memory

Agno's built-in memory system (`update_memory_on_run=True`) automatically extracts and stores important facts, preferences, and context from conversations. These are recalled in future sessions.

### 3. Workspace Files

The agent's workspace (`~/.vandelay/workspace/`) contains markdown files that shape its behavior and context. These are loaded into the system prompt at startup.

See [Workspace Files](../guides/workspace-files.md) for the full reference.

## Storage

All memory is stored in a unified SQLite database at `~/.vandelay/data/vandelay.db`. This handles:

- Session history
- Agentic memory records
- Session summaries

For PostgreSQL, set `db_url` in config or the `DATABASE_URL` environment variable.

## Shared Memory Across Channels

All channels (Terminal, Telegram, WhatsApp, WebSocket) use the same `user_id`, so memory is shared. A conversation in Telegram is remembered when you switch to Terminal.

## Token Management

History can grow large. Vandelay manages this with:

- Limited history runs (2 by default)
- Capped tool call results from history (5 by default)
- Session summaries that compress old conversations
