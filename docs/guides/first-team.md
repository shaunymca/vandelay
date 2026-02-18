# Your First Team

This guide walks you through setting up a team with specialist members.

## Prerequisites

- Vandelay installed and onboarded
- At least one tool enabled (e.g., `shell`, `file`)

## Step 1: Enable Team Mode

Team mode is on by default. Verify:

```bash
vandelay config  # → Team → check "enabled: true"
```

## Step 2: Add Members

The easiest way is through the CLI:

```bash
vandelay config  # → Team → Add member → Start from template
```

This opens a template picker with 14 starter templates. Pick one (e.g., CTO, DevOps, Personal Assistant) and it's added to your team.

### Manual Config

Or edit `config.json` directly:

```json
{
  "team": {
    "enabled": true,
    "members": [
      "vandelay-expert",
      "browser",
      "system",
      {
        "name": "my-researcher",
        "role": "Deep research specialist",
        "tools": ["tavily", "crawl4ai"],
        "instructions_file": "my-researcher.md"
      }
    ]
  }
}
```

## Step 3: Assign Tools

Members can only use tools that are:

1. Listed in the top-level `enabled_tools`
2. Assigned to the member via their `tools` list

Enable tools first:

```bash
vandelay tools enable shell file python tavily
```

## Step 4: Test Delegation

Start the agent and ask a question that requires a specific specialist:

```
You: Browse https://example.com and summarize the content
→ Supervisor delegates to browser specialist

You: List the files in my home directory
→ Supervisor delegates to system specialist
```

## How Delegation Works

The supervisor reads `AGENTS.md` from the workspace to decide which member handles each request. Edit `~/.vandelay/workspace/AGENTS.md` to customize delegation rules.

## Next Steps

- [Agent Templates](agent-templates.md) — Browse all 14 starter templates
- [Custom Tools](custom-tool.md) — Build tools for your specialists
- [Teams concept](../concepts/teams.md) — Understand team modes and architecture
