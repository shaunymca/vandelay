# Built-in Tools

These are Vandelay's custom toolkits, built specifically for the platform rather than sourced from Agno's third-party ecosystem.

## System Tools

### Shell (`shell`)

Execute shell commands on the host system.

- Runs commands via subprocess
- Respects [safety mode](../concepts/safety.md) (trust/confirm/tiered)
- Blocked patterns prevent dangerous commands
- Configurable timeout (default: 120s)

### File (`file`)

File system operations.

- Read, write, list, search files
- Write allowlist prevents modifications to protected paths
- `src/vandelay/` is blocked by default

### Python (`python`)

Execute Python code.

- Runs in a subprocess
- Access to installed packages
- Output captured and returned to agent

## Browser Tools

### Camoufox (`camoufox`)

Anti-detect Firefox browser via [Camoufox](https://github.com/daijro/camoufox).

- Playwright API (no Node.js needed)
- Lazy-starts browser on first use
- Navigate, screenshot, extract content, fill forms
- Anti-fingerprinting built in

## Scheduling & Notifications

### Scheduler (injected)

Cron job management. Automatically injected (not enabled via `tools enable`).

- `schedule_job()`: Create a cron job
- `list_scheduled_jobs()`: List all jobs
- `get_job_details()`: Get job info
- `pause_scheduled_job()` / `resume_scheduled_job()`: Toggle jobs
- `delete_scheduled_job()`: Remove a job

### Notify (injected)

Send proactive messages to the user. Automatically injected when a channel router is available.

- `notify_user()`: Send a message to the user's active channel
- `send_file()`: Send a file via the active channel

## Agent Management

### Workspace (injected)

Read and write workspace files (`SOUL.md`, `USER.md`, etc.).

### Tool Management (injected)

Enable, disable, and search tools at runtime.

### Member Management (injected)

Add, remove, and update team members at runtime.

### Task Queue (injected)

Create and manage tasks for async work.

### Deep Work (injected)

Launch autonomous background work sessions. Configurable via `deep_work` config.
