# Teams

Vandelay uses Agno's [Team](https://docs.agno.com/teams/overview) system to coordinate multiple specialist agents under a supervisor.

## How Teams Work

```
User Message
    ↓
Team Supervisor (leader)
    ↓ delegates to
┌────────────┬────────────┬────────────┐
│  Browser   │  System    │  Vandelay  │
│  Specialist│  Specialist│  Expert    │
│  (crawl4ai,│  (shell,   │  (file,    │
│  camoufox) │  file, py) │  python,   │
│            │            │  shell)    │
└────────────┴────────────┴────────────┘
```

The supervisor receives all messages, decides which specialist should handle the task, and delegates accordingly. Each member has scoped tools — they can only use what's assigned to them.

## Enabling Team Mode

Team mode is **on by default** since v0.1. Toggle it:

```bash
vandelay config  # → Team → Enable/Disable
```

Or in `config.json`:

```json
{
  "team": {
    "enabled": true,
    "members": ["vandelay-expert"]
  }
}
```

## Team Modes

| Mode | Behavior |
|------|----------|
| `coordinate` | Supervisor coordinates members, synthesizes responses (default) |
| `route` | Supervisor routes to one member, that member responds directly |
| `broadcast` | All members process the message, supervisor synthesizes |
| `tasks` | Supervisor breaks work into tasks, assigns to members |

## Built-in Specialists

| Name | Tools | Role |
|------|-------|------|
| `browser` | crawl4ai, camoufox | Web browsing, scraping, screenshots |
| `system` | shell, file, python | Shell commands, file ops, packages |
| `scheduler` | *(injected)* | Cron jobs, reminders, recurring tasks |
| `knowledge` | *(injected)* | Document search, RAG queries |
| `vandelay-expert` | file, python, shell | Agent builder — designs and improves team members |

## Custom Members

Define custom members in `config.json`:

```json
{
  "team": {
    "members": [
      "vandelay-expert",
      "browser",
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

See [Agent Templates](../guides/agent-templates.md) for starter templates and [Your First Team](../guides/first-team.md) for a step-by-step guide.
