# vandelay status

Show current configuration and agent status.

## Usage

```bash
vandelay status
```

## What It Shows

```
  Agent:     Art
  Model:     anthropic / claude-sonnet-4-6
  Safety:    normal
  Timezone:  America/New_York
  DB:        /home/user/.vandelay/data/vandelay.db
  Workspace: /home/user/.vandelay/workspace
  Channels:  Telegram
  Knowledge: enabled
  Team:      enabled (cto, project-manager, vandelay-expert)
  Server:    running at http://0.0.0.0:8000
  Docs:      http://0.0.0.0:8000/docs
  WS:        ws://0.0.0.0:8000/ws/terminal
```

| Field | Description |
|-------|-------------|
| Agent | Agent name from config |
| Model | Provider and model ID |
| Safety | Safety mode (`strict`, `normal`, or `off`) |
| Timezone | Timezone used for scheduling and heartbeat |
| DB | Path to the SQLite database |
| Workspace | Path to workspace markdown files |
| Channels | Active channels (Terminal only, Telegram, WhatsApp) |
| Knowledge | Whether RAG knowledge base is enabled |
| Team | Team mode status and member names |
| Server | Server URL if running, or "not running" |

## Notes

- Requires `vandelay onboard` to have been run first.
- The server status check connects to the configured port — if the daemon is installed and running, it shows as "running".
- Also available as a slash command inside terminal chat: `/status`
