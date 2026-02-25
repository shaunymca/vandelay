# vandelay start

Start the FastAPI server (and optionally a terminal chat session).

> **Typical workflow:** Run `vandelay` to open the TUI dashboard, then run
> `vandelay start` in a separate terminal to bring the server online.
> The TUI's Chat tab connects automatically once the server is running.

## Usage

```bash
vandelay start
```

## What It Does

1. Loads configuration from `~/.vandelay/config.json` and `~/.vandelay/.env`
2. Creates the agent (or team) with configured model, tools, and workspace
3. Starts the FastAPI server (default: `0.0.0.0:8000`)
4. Starts the scheduler engine (if cron jobs exist)
5. Registers Telegram/WhatsApp webhooks (if enabled)
6. Opens an interactive terminal chat session

## Options

| Flag | Description |
|------|-------------|
| `--server`, `-s` | Server only — no interactive terminal chat (for headless/daemon deployments) |
| `--watch`, `-w` | Auto-restart on file changes (watches src, config, and workspace files) |

## Environment Variables

| Variable | Effect |
|----------|--------|
| `VANDELAY_HOST` | Override server bind address |
| `VANDELAY_PORT` | Override server port |
| `VANDELAY_AUTO_ONBOARD=1` | Run headless onboarding automatically if no config exists (PaaS use) |
