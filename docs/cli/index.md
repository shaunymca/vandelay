# CLI Reference

Vandelay is managed through the `vandelay` CLI. Running it with no arguments opens the TUI dashboard.

## Global Usage

```bash
vandelay [command] [options]
```

Running `vandelay` with no subcommand opens the **TUI dashboard** — the recommended entry point. The onboarding wizard launches automatically on first run if no config exists.

## Commands

| Command | Description |
|---------|-------------|
| *(no args)* | Open the TUI dashboard (onboards automatically on first run) |
| [`onboard`](onboard.md) | CLI setup wizard (headless/scripted use) |
| [`start`](start.md) | Start the agent server and terminal chat |
| [`config`](config.md) | Interactive configuration editor |
| [`tools`](tools.md) | Manage tools (enable, disable, list, search) |
| [`cron`](cron.md) | Manage cron jobs |
| [`knowledge`](knowledge.md) | Manage knowledge/RAG corpus |
| [`memory`](memory.md) | View and manage agent memory |
| [`daemon`](daemon.md) | Install and manage the background daemon |
| `auth-google` | Google OAuth authentication flow |
| `--version` | Show version |
| `--help` | Show help |
