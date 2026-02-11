# Heartbeat

Short checklist for periodic wake-ups. Keep it small.

When you wake up for a heartbeat, run through this list. Only alert the user if something needs attention.

## Checks

1. **System health** — Disk space, memory, CPU. Alert if critical (>90%).
2. **Pending tasks** — Any scheduled jobs that failed or were missed?
3. **Service status** — Are monitored services/URLs responsive?

## Response Rules

- If everything is fine, respond with exactly: `HEARTBEAT_OK`
- If something needs attention, send a concise alert to the user's primary channel.
- Never bother the user unless there's a real problem.
- Keep alerts short and actionable.

## State

Track heartbeat state to avoid duplicate alerts. Use `memory/heartbeat-state.json` to batch periodic checks without over-communicating.
