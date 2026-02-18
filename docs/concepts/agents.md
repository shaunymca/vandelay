# Agents

Vandelay agents are built on [Agno's Agent class](https://docs.agno.com/agents/overview) with additional layers for workspace-driven prompts, hot-reloadable tools, and persistent memory.

## Agent Lifecycle

1. **Config loaded:** Settings read from `config.json`, `.env`, and environment variables
2. **Model created:** LLM provider initialized from `model.provider` and `model_id`
3. **Tools resolved:** Enabled tools instantiated from the tool registry
4. **Workspace assembled:** Seven markdown files compose the system prompt
5. **Agent created:** Agno `Agent` (or `Team`) instantiated with all components
6. **Ready:** Agent accepts messages via ChatService

## System Prompt Assembly

The system prompt is built from workspace files in `~/.vandelay/workspace/`:

| File | Purpose |
|------|---------|
| `SOUL.md` | Core personality, communication style, behavioral rules |
| `USER.md` | User preferences, context, personal details |
| `AGENTS.md` | Team delegation rules: which member handles what |
| `TOOLS.md` | Tool usage guidance, best practices per tool |
| `HEARTBEAT.md` | Proactive tasks to check during heartbeat |
| `BOOTSTRAP.md` | One-time startup instructions |
| `MEMORY.md` | Persistent notes the agent maintains |

These files are yours to edit. Changes take effect on the next agent reload.

## Hot Reload

When you enable or disable a tool (via CLI or chat), the agent is recreated with the new tool set without a server restart. The `AgentProvider` protocol ensures ChatService always gets the current agent instance.

## Single Agent vs Team

- **Single agent** (team disabled): One agent with all enabled tools
- **Team mode** (default): A supervisor delegates to specialist members with scoped tools

See [Teams](teams.md) for details on team mode.
