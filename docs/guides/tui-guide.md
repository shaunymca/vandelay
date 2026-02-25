# TUI Dashboard Guide

Vandelay's primary interface is a terminal dashboard built with [Textual](https://textual.textualize.io/). Run `vandelay` (with no arguments) to open it.

```
┌─────────────────────────────────────────────────────────┐
│  Vandelay  v0.x.x        [Restart] [Quit]               │
├──────────────────────────────────────────────────────────┤
│  Chat │ Status │ Config │ Agents │ Scheduler │ Knowledge │
│  Memory │ Workspace                                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  (tab content)                                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## First Run — Onboarding Wizard

On first launch, a welcome modal appears with two options:

- **Get Started** — opens the 5-step onboarding wizard
- **I know what I'm doing** — skips to the Config tab for manual setup

### Onboarding Steps

| Step | What to do |
|------|-----------|
| 1. Name | Enter your agent's name (default: Art) |
| 2. Provider | Select your AI provider (Anthropic, OpenAI, Google, Ollama, etc.) |
| 3. Auth | Enter your API key, or select Codex OAuth for OpenAI Codex |
| 4. Model | Choose a model from the live catalog for your provider |
| 5. Timezone | Confirm your timezone (auto-detected from system) |

Pressing **Finish** saves `~/.vandelay/config.json`, writes your API key to `~/.vandelay/.env`, and initialises the workspace. The TUI lands on the Chat tab ready to use.

---

## Tab Reference

### Chat

Send messages to your agent and receive streamed responses in real time. The Chat tab connects to the running server via WebSocket.

- Start the server first: `vandelay start --server` in a separate terminal, or install the daemon with `vandelay daemon install && vandelay daemon start`
- If the server is not running, the Chat tab shows a connection error
- Responses are rendered as Markdown

### Status

Live health overview:

- Agent name, model, provider, version
- Server URL and connection state
- Heartbeat last-run time and status
- Channel connection state (Telegram, WhatsApp)
- Team members and their status

### Config

Edit all settings without touching config files. Organised into sections:

**General**
- Agent name, user ID, timezone, workspace directory

**Model**
- Provider, model ID, auth method, API key

**Server**
- Host, port, database URL (SQLite path or `postgresql://` URL)
- Daemon controls: Install / Uninstall service
- Update Vandelay button (runs `git pull + uv sync + restart`)
- Daemon Logs viewer (refresh to pull latest)

**Heartbeat**
- Enable/disable, interval (minutes), active hours, timezone

**Safety**
- Safety mode (strict / normal / off)

Press **Save** in any section to persist changes. Changes that require a server restart (model, port, etc.) take effect after restarting.

### Agents

Manage the leader and team members.

**Leader** — subnav sections:
- **Name** — agent name and user ID
- **Model** — provider, model, auth method
- **Team** — enable/disable team mode, select coordination mode (coordinate / route / broadcast / tasks)
- **Tools** — add/remove tools, assign to members
- **Instructions** — edit SOUL.md directly

**Members** — click any member or **+ Add Agent** to:
- Set name, role, model (with optional per-member provider override)
- Assign tools
- Write custom instructions or pick a starter template
- Delete a member

### Scheduler

Manage cron jobs and view task history.

**Cron tab:**
- Table of all scheduled jobs: Name, Expression, Next Run, Last Run, Status, Type
- Toolbar: **Add**, **Edit**, **Enable/Disable**, **Delete**
- Heartbeat row is shown but cannot be edited or deleted (managed automatically)
- **Add / Edit modal**: set Name, Cron Expression (5-field standard cron), Command, Timezone

**Tasks tab:**
- Table of all queued tasks: ID, Created, Status, Command
- **Refresh** — reload from disk
- **Clear Completed** — remove done/failed entries

### Knowledge

Manage the agent's RAG knowledge base.

- **Enable/Disable** knowledge toggle
- **Status** — shows document count and last-indexed time
- **Add Document** — provide a file path or URL; select which agents to index it for (defaults to all: Shared + every team member)
- **Refresh Corpus** — re-index all documents
- **Clear Knowledge Base** — remove all indexed documents

### Memory

View and manage agent memories stored in the database.

- Table columns: ID, Topics, Memory (truncated), Created
- **Refresh** — reload from database
- **Delete Selected** — delete the highlighted memory row
- **Clear All** — remove all memories (with confirmation)

This tab shows Agno's agentic memory records — facts and context the agent has extracted and stored from conversations.

### Workspace

Edit the six workspace markdown files that compose the agent's system prompt.

File picker on the left:

| File | Purpose |
|------|---------|
| SOUL.md | Core personality and communication style |
| USER.md | Information about you: name, role, preferences |
| AGENTS.md | Team delegation rules |
| TOOLS.md | Tool usage guidance and best practices |
| HEARTBEAT.md | Checklist for periodic wake-ups |
| BOOTSTRAP.md | One-time startup instructions (auto-deleted after first read) |

Select a file to edit it. Changes are saved immediately and take effect on the next agent reload.

---

## Header Controls

| Control | Action |
|---------|--------|
| **Restart** | Restart the running daemon (or server) to apply config changes |
| **Quit** | Exit the TUI (does not stop the daemon or server) |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Move between tabs |
| `Enter` | Confirm / activate |
| `Escape` | Close modal / cancel |
| `Ctrl+C` | Quit |
