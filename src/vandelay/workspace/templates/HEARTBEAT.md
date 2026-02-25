# Heartbeat

Short checklist for periodic wake-ups. Keep it small.

When you wake up for a heartbeat, run through this list. Only alert the user if something needs attention.

## Checks

1. **Task queue** — Call check_open_tasks(). Resume in-progress tasks. Pick up pending tasks by priority. Mark stuck tasks as failed.
2. **System health** — Call `run_shell_command` directly yourself (do not delegate to a team member). The shell tool is always enabled for heartbeat. Invoke it like this: `run_shell_command(command="df -h /")`. Alert if critical (>90% disk/CPU or <100MB memory).
   - **Disk**: `run_shell_command(command="df -h /")`  — alert if >90% used.
   - **Memory**: `run_shell_command(command="free -m")` — alert if available column <100.
   - **CPU**: Use `/proc/stat` sampling — `run_shell_command(command="awk 'NR==1{u=$2;n=$3;s=$4;i=$5;w=$6;irq=$7;sirq=$8;st=$9;t=u+n+s+i+w+irq+sirq+st;print t,i+w}' /proc/stat")`, wait 1s, repeat, then compute `100*(dt - didle) / dt`. Do not use `top -bn1` — it gives false 100% readings on virtualized hosts.
3. **Scheduled jobs** — Call list_scheduled_jobs(). Check last_run and last_result for each enabled job. Alert if any job has failed, errored, or hasn't run when it should have. Note: the heartbeat job itself is not listed — if there are no user-defined jobs, "No scheduled jobs." is the expected response.
4. **Service status** — Are monitored services/URLs responsive?

## Response Rules

- If everything is fine, respond with exactly: `HEARTBEAT_OK`
- If something needs attention, send a concise alert to the user's primary channel.
- Never bother the user unless there's a real problem.
- Keep alerts short and actionable.

## State

Track heartbeat state to avoid duplicate alerts. Use `memory/heartbeat-state.json` to batch periodic checks without over-communicating.
