# Installation

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager
- An API key for at least one LLM provider (Anthropic, OpenAI, Google, Ollama, or OpenRouter)

## Install Vandelay

```bash
uv tool install vandelay
```

This installs the `vandelay` CLI globally. Verify it works:

```bash
vandelay --version
```

### Install from Source

For development or to run the latest code:

```bash
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync
uv tool install -e .
```

## Platform Notes

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | Full support | Recommended for production. systemd daemon included. |
| macOS | Full support | launchd daemon included. |
| Windows | Development only | Daemon not supported. Use WSL for production. |

## Next Steps

Once installed, run the interactive onboarding:

```bash
vandelay onboard
```

Or jump straight to the [Quickstart](quickstart.md).
