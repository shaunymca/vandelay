# vandelay tools

Manage agent tools — list, add, remove, browse, and inspect.

## Usage

```bash
vandelay tools <subcommand>
```

## Subcommands

### `list`

List all available tools:

```bash
vandelay tools list
vandelay tools list --enabled          # Show only enabled tools
vandelay tools list --category search  # Filter by category
vandelay tools list --builtin          # Show only built-in tools
```

Output includes name, category, pricing, status, and dependencies.

### `add`

Enable a tool and install its dependencies:

```bash
vandelay tools add shell
vandelay tools add duckduckgo
vandelay tools add tavily gmail googlecalendar
vandelay tools add camoufox --no-install  # Enable without installing deps
```

If team mode is enabled, you'll be prompted to assign the tool to team members.

Restart the agent (or run `vandelay update`) for the tool to take effect.

### `remove`

Disable a tool:

```bash
vandelay tools remove tavily
vandelay tools remove camoufox --uninstall  # Also remove pip dependencies
```

### `browse`

Interactively browse, inspect, and enable/disable tools:

```bash
vandelay tools browse
```

Walks through filter → list → detail → action. The easiest way to explore what's available.

### `info`

Show details for a specific tool:

```bash
vandelay tools info shell
vandelay tools info duckduckgo
```

Displays class, module, category, pricing, dependencies, installed status, and enabled status.

### `refresh`

Rebuild the tool registry from the installed Agno package:

```bash
vandelay tools refresh
```

Use this after upgrading Agno or adding new custom tools. The registry is cached at `~/.vandelay/tool_registry.json`.

### `auth-google`

Authenticate all Google services (Gmail, Calendar, Drive, Sheets) with a single OAuth flow:

```bash
vandelay tools auth-google
vandelay tools auth-google --reauth  # Re-authenticate even if token exists
```

Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_PROJECT_ID` in `~/.vandelay/.env`. Token is saved to `~/.vandelay/google_token.json` and covers all four Google services. Use the headless console flow — no browser needed on the server.

### `create`

Scaffold a custom tool template:

```bash
vandelay tools create my_tool
```

Creates `~/.vandelay/custom_tools/my_tool.py` with a `MyToolTools` class ready to extend. After editing:

```bash
vandelay tools refresh   # Register the new tool
vandelay tools add my_tool  # Enable it
```

See [Custom Tools](../guides/custom-tools.md) for a full walkthrough.

## How Tools Are Resolved

1. Tool slugs in `enabled_tools` are looked up in the tool registry
2. The registry maps slugs to Agno toolkit classes (or Vandelay custom toolkits)
3. Toolkits are instantiated and attached to the agent (or the team leader and designated members)

## Tool Assignment in Teams

When team mode is enabled, tools are assigned per-member via their `tools` list. A member can only use tools that are both:

- In the top-level `enabled_tools`
- In the member's `tools` list

The team leader also receives all `enabled_tools` directly, so it can act without delegating when appropriate.

See [Your First Team](../guides/first-team.md) for details.
