# Installation

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/):** Fast Python package manager
- An API key for at least one LLM provider (Anthropic, OpenAI, Google, Ollama, or OpenRouter)

## Install Vandelay

Vandelay is currently distributed from source. Install via git:

```bash
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync
uv tool install -e .
```

Verify it works:

```bash
vandelay --version
```

> **PyPI release coming soon.** Once published, installation will simplify to `uv tool install vandelay`.

## Platform Notes

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | Full support | Recommended for production. systemd daemon included. |
| macOS | Full support | launchd daemon included. |
| Windows | Development only | Daemon not supported. Use WSL for production. |

## Next Steps

Once installed, open the Vandelay TUI dashboard:

```bash
vandelay
```

If this is your first time, the onboarding wizard will appear automatically to set up your provider and API key. See the [Quickstart](quickstart.md) for the full walkthrough.
