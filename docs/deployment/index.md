# Deployment

Vandelay is built for self-hosted deployment. Your agent runs on your server, with your data, under your control.

## Deployment Options

| Path | Best For | Guide |
|------|----------|-------|
| [VPS](vps.md) | Production — Ubuntu/Debian server with systemd | Recommended |
| Local | Development — run `vandelay start` on your machine | [Quickstart](../getting-started/quickstart.md) |

## What You Need

- A Linux server (Ubuntu 22.04+ recommended)
- Python 3.11+
- An API key for your LLM provider
- A domain name (optional, for Telegram webhooks)

## Architecture in Production

```
Internet
    ↓
Nginx (reverse proxy, TLS)
    ↓ :8000
Vandelay (FastAPI + uvicorn)
    ↓
systemd (daemon management)
```

The daemon runs Vandelay as a background service with automatic restart on failure. Nginx handles TLS termination and proxies requests to the FastAPI server.

## Quick Deploy

```bash
# On your server
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync
uv tool install -e .
vandelay onboard
vandelay daemon install
vandelay daemon start
```

See the [VPS guide](vps.md) for the full walkthrough with Nginx, firewall, and security hardening.
