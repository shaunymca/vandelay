# vandelay tools

Manage the tool registry — enable, disable, list, and search tools.

## Usage

```bash
vandelay tools <subcommand>
```

## Subcommands

### `enable`

Enable one or more tools:

```bash
vandelay tools enable shell file python
vandelay tools enable tavily gmail googlecalendar
```

Enabled tools are added to `enabled_tools` in `config.json` and become available to the agent.

### `disable`

Disable a tool:

```bash
vandelay tools disable tavily
```

### `list`

List all enabled tools:

```bash
vandelay tools list
```

### `search`

Search available tools by name or category:

```bash
vandelay tools search "search"
vandelay tools search "google"
```

## How Tools Are Resolved

1. Tool slugs in `enabled_tools` are looked up in the tool registry
2. The registry maps slugs to Agno toolkit classes (or Vandelay custom toolkits)
3. Toolkits are instantiated and attached to the agent (or assigned to team members)

## Tool Assignment in Teams

When team mode is enabled, tools are assigned to members via their `tools` list. A member can only use tools that are both:

- In the top-level `enabled_tools`
- In the member's `tools` list

See [Your First Team](../guides/first-team.md) for details.
