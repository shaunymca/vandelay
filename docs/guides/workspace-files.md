# Workspace Files

Vandelay assembles the agent's system prompt from seven markdown files in `~/.vandelay/workspace/`. Each file controls a different aspect of agent behavior.

## File Reference

### SOUL.md

The agent's core personality and communication style.

- Defines tone, formality, language preferences
- Sets behavioral rules (e.g., "always confirm before destructive actions")
- This is the most important file; it shapes how the agent acts

### USER.md

Information about you, the user.

- Name, role, preferences
- Project context and goals
- Personal details the agent should know

### AGENTS.md

Team delegation rules.

- Defines which specialist handles which task type
- Controls how the supervisor routes requests
- Only relevant when team mode is enabled

### TOOLS.md

Tool usage guidance.

- Best practices per tool
- When to use which tool
- Tool-specific instructions (e.g., "always use --verbose with shell commands")

### HEARTBEAT.md

Proactive tasks for the heartbeat system.

- List of things the agent should check periodically
- Evaluated during each heartbeat interval
- Only relevant when heartbeat is enabled

### BOOTSTRAP.md

One-time startup instructions.

- Tasks to run when the agent first starts
- Initialization checks, welcome messages
- Evaluated once per server start

### MEMORY.md

Persistent notes maintained by the agent.

- The agent reads and writes to this file
- Stores important context, decisions, action items
- Included in the system prompt every run

## Editing

Edit any file directly:

```bash
nano ~/.vandelay/workspace/SOUL.md
```

Or ask the agent to update its own workspace files. It has `WorkspaceTools` for reading and writing these files directly.

Changes take effect on the next agent reload (automatic when using `WorkspaceTools`).

## Default Templates

On first `vandelay onboard`, default templates are written for each file. These provide a reasonable starting point that you can customize over time.
