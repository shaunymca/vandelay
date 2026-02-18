# vandelay cron

Manage cron jobs from the command line.

## Usage

```bash
vandelay cron <subcommand>
```

## Subcommands

### `list`

List all cron jobs:

```bash
vandelay cron list
```

### `add`

Create a new cron job:

```bash
vandelay cron add --name "morning-email" --schedule "0 8 * * *" --command "Check my email and summarize anything important"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--name` | Yes | Unique job identifier |
| `--schedule` | Yes | Cron expression (5-field) |
| `--command` | Yes | The message to send to the agent |

### `remove`

Remove a cron job:

```bash
vandelay cron remove morning-email
```

### `pause` / `resume`

Pause or resume a cron job:

```bash
vandelay cron pause morning-email
vandelay cron resume morning-email
```

## Cron Expressions

Standard 5-field format: `minute hour day month weekday`

| Expression | Meaning |
|-----------|---------|
| `0 8 * * *` | Daily at 8:00 AM |
| `0 9 * * 1` | Mondays at 9:00 AM |
| `*/30 * * * *` | Every 30 minutes |
| `0 19 * * 1-5` | Weekdays at 7:00 PM |
| `0 0 1 * *` | First of every month at midnight |

## Storage

Jobs are persisted in `~/.vandelay/cron_jobs.json` and restored on startup.

## Agent-Created Jobs

The agent can also create cron jobs via chat using the `schedule_job()` tool. These appear in `vandelay cron list` alongside CLI-created jobs.
