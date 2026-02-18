# vandelay onboard

Interactive setup wizard. Creates your initial configuration and workspace.

## Usage

```bash
vandelay onboard
```

## What It Does

1. **Model selection:** Pick from 10 LLM providers, fetches available models in real time
2. **API key:** Securely stored in `~/.vandelay/.env`
3. **Config creation:** Writes `~/.vandelay/config.json` with sensible defaults
4. **Workspace setup:** Creates 7 workspace markdown files in `~/.vandelay/workspace/`

## Options

| Flag | Description |
|------|-------------|
| `--headless` | Non-interactive mode for servers without a TTY |

## Environment Variables

| Variable | Effect |
|----------|--------|
| `VANDELAY_AUTO_ONBOARD=1` | Auto-run onboard on first `vandelay start` if no config exists |

## Re-running

Safe to re-run. Existing config values are preserved as defaults in the prompts. Workspace files are only created if they don't exist.
