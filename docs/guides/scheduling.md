# Scheduling

Set up cron jobs, heartbeat, and active hours for autonomous agent behavior.

## Cron Jobs

Cron jobs let the agent perform tasks on a schedule — checking email, updating spreadsheets, running reports, etc.

### Creating via Chat

Ask your agent:

```
You: Create a cron job that checks my email every morning at 8am
You: Schedule a daily fitness check-in at 7pm ET
You: Set up a weekly report every Monday at 9am
```

The agent uses `schedule_job()` to create the cron entry.

### Creating via CLI

```bash
vandelay cron add --name "morning-email" --schedule "0 8 * * *" --command "Check my email and summarize anything important"
vandelay cron list
vandelay cron remove morning-email
```

### Cron Expression Format

Standard 5-field cron syntax: `minute hour day month weekday`

| Expression | Meaning |
|-----------|---------|
| `0 8 * * *` | Every day at 8:00 AM |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `*/30 * * * *` | Every 30 minutes |
| `0 19 * * 1-5` | Weekdays at 7:00 PM |

### How Cron Jobs Execute

When a cron job fires, the scheduler sends the command through `ChatService` as if it were a user message. The agent (or team) processes it normally, with full access to tools and memory.

Jobs are persisted in `~/.vandelay/cron_jobs.json` and restored on startup.

## Heartbeat

The heartbeat is a periodic check-in where the agent evaluates proactive tasks defined in `HEARTBEAT.md`.

### Enabling

```json
{
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 30,
    "active_hours_start": 8,
    "active_hours_end": 22,
    "timezone": "America/New_York"
  }
}
```

### Active Hours

The heartbeat only fires within the active hours window. Outside this window, the agent stays quiet.

### What Happens on Heartbeat

The agent reads `~/.vandelay/workspace/HEARTBEAT.md` and evaluates each task. Edit this file to define what the agent should check proactively.

## Next Steps

- [CLI Reference: cron](../cli/cron.md) — Full cron command reference
- [Deployment](../deployment/vps.md) — Run scheduling 24/7 on a VPS
