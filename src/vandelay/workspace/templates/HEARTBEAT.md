# Heartbeat

Short checklist for periodic wake-ups. Keep it small.

When you wake up for a heartbeat, run through this list. Only alert the user if something needs attention.

## Checks

1. **Task queue** — Call check_open_tasks(). Resume in-progress tasks. Pick up pending tasks by priority. Mark stuck tasks as failed.
2. **System health** — Run these shell commands yourself (do not delegate to a team member). Alert if critical (>90% disk/CPU or <100MB memory).
   - **CPU**: Use `/proc/stat` sampling (not `top -bn1` — it gives false 100% readings on virtualized hosts). Example: `read -r cpu user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat; idle1=$((idle+iowait)); total1=$((user+nice+system+idle+iowait+irq+softirq+steal)); sleep 1; read -r cpu user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat; idle2=$((idle+iowait)); total2=$((user+nice+system+idle+iowait+irq+softirq+steal)); echo "$((100*(total2-total1-(idle2-idle1))/(total2-total1)))%"`
   - **Disk**: `df -h /` — alert if >90% used.
   - **Memory**: `free -m` — alert if <100MB available.
3. **Scheduled jobs** — Call list_scheduled_jobs(). Check last_run and last_result for each enabled job. Alert if any job has failed, errored, or hasn't run when it should have.
4. **Service status** — Are monitored services/URLs responsive?

## Response Rules

- If everything is fine, respond with exactly: `HEARTBEAT_OK`
- If something needs attention, send a concise alert to the user's primary channel.
- Never bother the user unless there's a real problem.
- Keep alerts short and actionable.

## State

Track heartbeat state to avoid duplicate alerts. Use `memory/heartbeat-state.json` to batch periodic checks without over-communicating.
