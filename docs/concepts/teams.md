# Teams

Vandelay uses Agno's [Team](https://docs.agno.com/teams/overview) system to coordinate multiple specialist agents under a supervisor.

## How Teams Work

```
User Message
    ↓
Team Supervisor (leader)
    ↓ delegates to
┌─────────────────┬──────────────────────────┐
│  Vandelay Expert│  Your Custom Specialists  │
│  (file, python, │  (any tools, any role)    │
│   shell)        │                           │
└─────────────────┴──────────────────────────┘
```

The supervisor receives all messages, decides which specialist should handle the task, and delegates accordingly. Each member has scoped tools: they can only use what's assigned to them.

## Enabling Team Mode

Team mode is **on by default in coordinate mode**. You can toggle it:

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

## The Vandelay Expert

Vandelay ships with one default specialist: the **Vandelay Expert**.

| Name | Tools | Role |
|------|-------|------|
| `vandelay-expert` | file, python, shell | Designs, creates, tests, and improves team members |

The Vandelay Expert is your agent builder and platform authority. It can evolve your setup over time without you touching config files manually. It can:

- **Write and edit member instructions:** draft prompts, refine personas, fix vague or conflicting guidance
- **Assign tools to members:** enable tools and scope them to the right specialists
- **Apply starter templates:** pick from 14 prebuilt personas (CTO, Researcher, DevOps, etc.) and customize them
- **Set up cron jobs:** schedule recurring tasks with cron expressions and timezones
- **Configure the heartbeat:** set what the agent checks and acts on autonomously while idle
- **Manage the team:** add, remove, and reconfigure specialists as your needs change
- **Diagnose underperforming agents:** identify prompt issues, wrong tool assignments, token overflow, and missing context
- **Design custom tools:** scaffold new toolkits when built-in tools don't cover a use case

It ships enabled by default. To remove it, edit `config.json`:

```json
{
  "team": {
    "members": []
  }
}
```

All other members are defined fully in `config.json` — no magic names.

## Custom Members

Every other team member is defined by you. Add members in `config.json` with any combination of tools, role description, and instruction file:

```json
{
  "team": {
    "members": [
      "kramer",
      {
        "name": "Kramer",
        "role": "wild brainstorming, unfiltered first drafts, and lateral thinking",
        "tools": ["wikipedia", "camoufox"],
        "instructions_file": "kramer.md"
      }
    ]
  }
}
```

See [Agent Templates](../guides/agent-templates.md) for starter templates and [Your First Team](../guides/first-team.md) for a step-by-step guide.
