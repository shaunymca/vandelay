# Scheduling

Set up cron jobs, heartbeat, and active hours for autonomous agent behavior.

## Cron Jobs

Cron jobs let the agent perform tasks on a schedule: checking email, updating spreadsheets, running reports, and more.

### Creating via the TUI Scheduler Tab

Open the TUI dashboard (`vandelay`) and go to the **Scheduler** tab → **Cron** sub-tab.

- **Add:** Click `+ Add` to open the job editor. Fill in the name, cron expression (5-field standard format), command, and timezone.
- **Edit:** Select a job row and click `✎ Edit`.
- **Enable / Disable:** Select a job row and click `◉ Enable` or `◎ Disable` to toggle it without deleting.
- **Delete:** Select a job row and click `✕ Delete`.

The heartbeat job (if enabled) appears in the list but cannot be edited or deleted from this view — configure it in the **Heartbeat** sub-tab instead.

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

### Timezones

Cron jobs and the heartbeat default to your configured timezone (set during onboarding or via `/config` → Timezone). You don't need to specify it every time:

```
You: Schedule a daily report at 9am
```

To override for a specific job, include the timezone in your request:

```
You: Schedule a weekly backup at midnight London time
```

Or via CLI (omit `--tz` to use your configured timezone):

```bash
vandelay cron add "daily-report" "0 9 * * *" "Generate daily report"
# Uses settings.timezone automatically

vandelay cron add "london-backup" "0 0 * * 0" "Weekly backup" --tz "Europe/London"
# Explicit override
```

To change your default timezone: `vandelay config` → Timezone.

### How Cron Jobs Execute

When a cron job fires, the scheduler sends the command through `ChatService` as if it were a user message. The agent (or team) processes it normally, with full access to tools and memory, using your user ID so it shares your conversation history and memory.

Jobs are persisted in `~/.vandelay/cron_jobs.json` and restored on startup.

## Heartbeat

The heartbeat is a periodic check-in where the agent evaluates proactive tasks defined in `HEARTBEAT.md`.

### Configuring via the TUI

Open the TUI dashboard (`vandelay`) and go to **Scheduler** → **Heartbeat** sub-tab:

| Field | Description |
|-------|-------------|
| **Enable heartbeat** | Toggle on/off |
| **Interval (minutes)** | How often the heartbeat fires within active hours |
| **Active from / to** | 24-hour window during which the heartbeat is allowed to run |
| **Timezone** | Timezone for the active hours window |

Click **Save** to persist changes immediately to `~/.vandelay/config.json`.

The current heartbeat status (on/off, interval, active window) is also visible at a glance on the **Status** tab.

### Configuring via config.json

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

`HEARTBEAT.md` is loaded into the agent's system prompt at startup, so the agent knows its checklist without any extra file reads. When the heartbeat fires, the agent runs through its checklist and responds with `HEARTBEAT_OK` if everything is fine, or alerts you via your primary channel if something needs attention.

The default checklist:

1. Call `check_open_tasks()` — resume in-progress work, pick up pending tasks by priority
2. Check system health (disk, memory, CPU) — alert if critical
3. Check for any missed scheduled jobs
4. Check monitored services

Edit `~/.vandelay/workspace/HEARTBEAT.md` to customize what the agent checks.

## Next Steps

- [CLI Reference: cron](../cli/cron.md) - Full cron command reference
- [Deployment](../deployment/vps.md) - Run scheduling 24/7 on a VPS
