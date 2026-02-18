# vandelay config

Interactive configuration editor with a menu-driven interface.

## Usage

```bash
vandelay config
```

## Menu Structure

```
Config
├── Model: Provider, model ID, API key
├── Agent: Name, user ID, timezone
├── Tools: Enable/disable tools
├── Safety: Safety mode, allowed commands, blocked patterns
├── Channels: Telegram, WhatsApp settings
├── Heartbeat: Enable, interval, active hours
├── Team: Enable, members, add/remove members
├── Knowledge: Enable, embedder settings
├── Deep Work: Enable, activation mode, limits
└── Server: Host, port, secret key
```

## Features

- **Live editing:** Changes are written to `config.json` immediately
- **Daemon restart:** If a daemon is running, offers to restart it to apply changes
- **Model picker:** Fetches available models from your provider in real time
- **Template picker:** Browse 14 starter templates when adding team members
- **Member model editing:** Override model provider/ID per team member

## Config File

All changes are persisted to `~/.vandelay/config.json`. See the [Configuration Reference](../configuration/index.md) for the full schema.
