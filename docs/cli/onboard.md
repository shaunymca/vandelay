# vandelay onboard

CLI setup wizard for headless or non-interactive environments.

> **Recommended for most users:** Run `vandelay` to open the TUI dashboard instead.
> The onboarding wizard runs automatically inside the TUI on first launch —
> no need to run this command separately.

## Usage

```bash
vandelay onboard
```

## When to Use This

- **Headless servers** without a terminal UI (use `--non-interactive` with env vars)
- **CI/CD pipelines** where you want to script the initial setup
- **Scripted deployments** where you prefer CLI-only configuration

For interactive use on a desktop or laptop, `vandelay` (no arguments) is the better entry point.

## What It Does

1. **Agent name:** Set what to call your agent
2. **Provider:** Pick from 10 LLM providers (Anthropic, OpenAI, Google, Ollama, etc.)
3. **Auth / API key:** API key stored in `~/.vandelay/.env`; Ollama skips this step; OpenAI subscription uses OAuth
4. **Model:** Select the specific model from a curated list for the chosen provider
5. **Timezone:** Used for scheduling and cron jobs
6. **Config creation:** Writes `~/.vandelay/config.json` with sensible defaults
7. **Workspace setup:** Creates 7 workspace markdown files in `~/.vandelay/workspace/`

## Options

| Flag | Description |
|------|-------------|
| `--non-interactive` / `-n` | Headless mode — reads config from environment variables |

## Environment Variables (Headless Mode)

| Variable | Effect |
|----------|--------|
| `VANDELAY_AUTO_ONBOARD=1` | Auto-run onboard on first `vandelay start` if no config exists |

## Re-running

Safe to re-run. Existing config values are preserved as defaults. Workspace files are only created if they don't exist.
