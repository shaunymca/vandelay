# Deployment Guide

This guide covers local development, PaaS deployment (Railway), and VPS deployment with network isolation (Tailscale).

> **Important:** Vandelay exposes an API that can execute shell commands. Always deploy behind authentication and network isolation in production.

---

## Table of Contents

- [Local Development](#local-development)
- [Deploy to Railway](#deploy-to-railway)
- [Deploy to a VPS](#deploy-to-a-vps)
- [Network Isolation with Tailscale](#network-isolation-with-tailscale)
- [Webhook Configuration](#webhook-configuration)
- [Security Hardening](#security-hardening)
- [AgentOS Control Panel](#agentos-control-panel)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Quick Reference](#quick-reference)

---

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An API key from Anthropic, OpenAI, Google, OpenRouter, or a local Ollama install

### Setup

```bash
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync
uv run vandelay onboard
uv run vandelay start
```

The onboard wizard walks you through 8 steps: identity, model, safety mode, timezone, browser tools, workspace, channels, and knowledge base.

After setup, the following services are available:

| Service | URL |
|---------|-----|
| Terminal chat | Console prompt |
| FastAPI server | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| WebSocket | `ws://localhost:8000/ws/terminal` |
| AgentOS | [os.agno.com](https://os.agno.com) (connect your endpoint) |

### Verify

```bash
curl http://localhost:8000/health
uv run pytest tests/ -v
```

---

## Deploy to Railway

[Railway](https://railway.app) is a PaaS that deploys from GitHub with no server management required.

### 1. Push to GitHub

```bash
git remote add origin https://github.com/shaunymca/vandelay.git
git push -u origin master
```

### 2. Create a Railway project

1. Sign in at [railway.app](https://railway.app) with GitHub
2. **New Project** > **Deploy from GitHub repo**
3. Select your Vandelay repository
4. Railway auto-detects Python from `pyproject.toml`

### 3. Set environment variables

In **Variables**, add:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `GOOGLE_API_KEY` | Yes* | Google AI API key |
| `VANDELAY_PORT` | Yes | Set to `${{PORT}}` (Railway's dynamic port) |
| `VANDELAY_HOST` | No | Defaults to `0.0.0.0` |
| `VANDELAY_SECRET_KEY` | Recommended | JWT signing key for API auth |
| `TELEGRAM_TOKEN` | No | Telegram bot token |
| `TELEGRAM_CHAT_ID` | No | Lock bot to one chat |
| `WHATSAPP_ACCESS_TOKEN` | No | WhatsApp Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | No | WhatsApp phone number ID |

*At least one model provider key is required.*

### 4. Configure the start command

In **Settings** > **Deploy** > **Start Command**:

```
vandelay start --server
```

This runs in headless mode (API + WebSocket + webhooks, no terminal chat).

### 5. Add persistent storage

Attach a volume to preserve state across deploys:

1. Click **New** > **Volume**
2. Set the mount path to `/root/.vandelay`
3. Attach it to your Vandelay service

This persists the SQLite database, workspace templates, config, and cron jobs.

### 6. Custom domain (optional)

1. **Settings** > **Networking** > **Custom Domain**
2. Add your domain (e.g., `vandelay.yourdomain.com`)
3. Point your DNS CNAME to the Railway-provided target
4. Railway handles TLS automatically

### 7. Set up webhooks

**Telegram:**
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://vandelay.yourdomain.com/webhooks/telegram"
```

**WhatsApp:**
In your [Meta Developer Console](https://developers.facebook.com/), set the webhook URL to:
```
https://vandelay.yourdomain.com/webhooks/whatsapp
```

### 8. Verify

```bash
curl https://vandelay.yourdomain.com/health
curl https://vandelay.yourdomain.com/status
```

### Ongoing management

| Task | How |
|------|-----|
| Redeploy | Push to GitHub (auto-deploys) |
| Logs | Railway dashboard > **Deployments** > **View Logs** |
| Add tools | Railway shell: `vandelay tools add <name>` |
| Update config | Change env vars in dashboard (auto-restarts) |

### Pricing

The Hobby plan ($5/month) removes sleep limits. The free tier includes $5/month in credits.

> **Note:** Railway containers are internet-facing. Set `VANDELAY_SECRET_KEY` for API auth and use `TELEGRAM_CHAT_ID` to restrict bot access. For full network isolation, use the VPS + Tailscale path below.

---

## Deploy to a VPS

### Providers

Any Ubuntu 22.04+ or Debian 12+ VPS works. Example providers:

| Provider | Spec | Cost |
|----------|------|------|
| Hetzner | 2 vCPU, 4GB RAM, 40GB SSD | ~$7/mo |
| DigitalOcean | 2 vCPU, 4GB RAM, 80GB SSD | ~$24/mo |
| AWS Lightsail | 2 vCPU, 4GB RAM, 80GB SSD | ~$20/mo |

### 1. Provision the server

Create a VPS with SSH key authentication.

### 2. Initial server setup

```bash
ssh root@your-server-ip

# Create a non-root user
adduser vandelay
usermod -aG sudo vandelay
su - vandelay
```

### 3. Install dependencies

```bash
sudo apt update && sudo apt install -y git curl build-essential

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Install Python 3.11+ (if not already present)
sudo apt install -y python3.11 python3.11-venv
```

### 4. Deploy Vandelay

```bash
git clone https://github.com/shaunymca/vandelay.git ~/vandelay
cd ~/vandelay
uv sync

uv run vandelay onboard

# Verify it starts
uv run vandelay start --server
# Ctrl+C to stop
```

### 5. Install as a system service

```bash
uv run vandelay daemon install
uv run vandelay daemon start
uv run vandelay daemon status
```

On Linux, this creates a user-level systemd unit at `~/.config/systemd/user/vandelay.service`. On macOS, it creates a LaunchAgent at `~/Library/LaunchAgents/com.vandelay.agent.plist`. The service auto-restarts on failure with a 5-second delay. No sudo required.

```bash
uv run vandelay daemon stop       # Stop the service
uv run vandelay daemon restart    # Restart
uv run vandelay daemon logs       # Tail logs
uv run vandelay daemon uninstall  # Remove the service
```

> **Note:** Do not open ports yet. Configure Tailscale first (next section).

---

## Network Isolation with Tailscale

[Tailscale](https://tailscale.com) creates an encrypted mesh VPN between your devices. Your server gets a private IP (100.x.x.x) reachable only by authorized devices.

### 1. Install Tailscale on the server

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Note your Tailscale IP
tailscale ip -4
# Output: 100.x.x.x
```

### 2. Install Tailscale on your devices

- **Desktop**: [tailscale.com/download](https://tailscale.com/download)
- **Mobile**: App Store / Google Play
- **Other servers**: Same `curl | sh` install

### 3. Bind Vandelay to the Tailscale interface

```bash
# In ~/.vandelay/.env
VANDELAY_HOST=100.x.x.x    # Your Tailscale IP
VANDELAY_PORT=8000
```

```bash
vandelay daemon restart
```

Verify the bind address:

```bash
sudo ss -tulpn | grep 8000
# Should show 100.x.x.x:8000, NOT 0.0.0.0:8000
```

### 4. Configure the firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0
sudo ufw enable
```

### 5. Verify access

From a device on your Tailnet:

```bash
curl http://100.x.x.x:8000/health
# Expected: {"status": "ok"}
```

From outside your Tailnet:

```bash
curl http://your-public-ip:8000/health
# Expected: connection refused
```

### 6. Tailscale SSH (optional)

Replace traditional SSH with identity-based access:

```bash
# On the server
sudo tailscale up --ssh

# On your client (no SSH keys needed)
ssh vandelay@vandelay-server
```

Access is controlled by your Tailscale ACLs.

---

## Webhook Configuration

Telegram and WhatsApp require a public HTTPS URL for webhooks.

### Option A: Tailscale Funnel

Funnel exposes a single port publicly through Tailscale's edge network with automatic TLS.

```bash
sudo tailscale serve --bg https+insecure://localhost:8000
sudo tailscale funnel 443 on
```

Your server is reachable at `https://vandelay-server.your-tailnet.ts.net`.

Set webhooks:

```bash
# Telegram
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://vandelay-server.your-tailnet.ts.net/webhooks/telegram"
```

For WhatsApp, set the webhook URL in your [Meta Developer Console](https://developers.facebook.com/) to:
```
https://vandelay-server.your-tailnet.ts.net/webhooks/whatsapp
```

### Option B: nginx reverse proxy

Expose only webhook paths through a custom domain:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

```nginx
# /etc/nginx/sites-available/vandelay
server {
    listen 80;
    server_name vandelay.yourdomain.com;

    location /webhooks/ {
        proxy_pass http://100.x.x.x:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        return 403;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vandelay /etc/nginx/sites-enabled/
sudo certbot --nginx -d vandelay.yourdomain.com
sudo systemctl reload nginx

sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Only `/webhooks/*` is publicly accessible. All other endpoints remain Tailscale-only.

### Option C: No webhooks

If you only use terminal chat or the WebSocket API, skip this section.

---

## Security Hardening

### SSH

```bash
sudo nano /etc/ssh/sshd_config
```

```
PasswordAuthentication no
PermitRootLogin no
MaxAuthTries 3
```

If using Tailscale SSH, bind to the Tailscale interface:

```
ListenAddress 100.x.x.x
```

```bash
sudo systemctl restart sshd
```

### File permissions

```bash
chmod 700 ~/.vandelay
chmod 600 ~/.vandelay/.env
chmod 600 ~/.vandelay/config.json
chmod 644 ~/.vandelay/data/vandelay.db
```

### Automatic OS updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Safety mode

Use **Tiered** or **Confirm** safety mode in production:

```bash
uv run vandelay status

# Or edit directly
nano ~/.vandelay/config.json
# Set "safety_mode": "tiered"
```

### Database backups

```bash
crontab -e
```

```cron
0 3 * * * cp ~/.vandelay/data/vandelay.db ~/.vandelay/data/vandelay.db.bak
```

For PostgreSQL, use `pg_dump`.

---

## AgentOS Control Panel

[AgentOS](https://docs.agno.com/agent-os/connect-your-os) is Agno's hosted control panel at [os.agno.com](https://os.agno.com). It connects directly from your browser to your running Vandelay server — no data is routed through Agno's servers.

### Connect your agent

1. Ensure your Vandelay server is running (`vandelay start --server` or `vandelay daemon start`)
2. Go to [os.agno.com](https://os.agno.com) and sign in
3. Click **Add new OS**
4. Fill in:
   - **Environment** — Local Development or Production
   - **Endpoint URL** — your server address (see table below)
   - **OS Name** — a label for this instance (e.g. "Vandelay Production")
   - **Tags** — optional
5. Click **CONNECT**

| Deployment | Endpoint URL |
|------------|-------------|
| Local | `http://localhost:8000` |
| Tailscale | `http://100.x.x.x:8000` (from a device on your Tailnet) |
| Railway | `https://vandelay.yourdomain.com` |
| VPS (public) | `https://vandelay.yourdomain.com` (via Funnel or nginx) |

### Features

| Feature | Description |
|---------|-------------|
| Chat | Web-based chat with streaming responses |
| Sessions | Browse and resume past conversations |
| Memory | View what the agent remembers across sessions |
| Knowledge | See indexed documents and RAG sources |

### Access requirements

Your Vandelay endpoint must be reachable from your browser for AgentOS to connect.

- **Local development:** Works out of the box at `localhost:8000`
- **Tailscale:** Connect from a device on your Tailnet
- **Public deployments:** Ensure TLS is configured (Railway handles this automatically; for VPS, use Tailscale Funnel or nginx with certbot)

---

## Monitoring & Maintenance

### Service health

```bash
vandelay daemon status
vandelay daemon logs
curl http://100.x.x.x:8000/health
```

### Updating

```bash
cd ~/vandelay
git pull
uv sync
vandelay daemon restart
```

### Updating Tailscale

```bash
sudo apt update && sudo apt upgrade tailscale
```

### Port audit

```bash
sudo ss -tulpn | grep LISTEN
# All listeners should be on 100.x.x.x or 127.0.0.1
```

---

## Quick Reference

### Pre-deployment checklist

- [ ] Tailscale installed on server and client devices
- [ ] `VANDELAY_HOST` set to Tailscale IP (100.x.x.x)
- [ ] UFW: deny all incoming, allow tailscale0
- [ ] SSH: no password auth, no root login
- [ ] File permissions: `~/.vandelay/` is 700, `.env` is 600
- [ ] Safety mode set to Tiered or Confirm
- [ ] Webhooks routed through Funnel or nginx (if needed)
- [ ] Automatic OS updates enabled
- [ ] Database backup cron job configured

### Common commands

```bash
# Daemon
vandelay daemon start
vandelay daemon stop
vandelay daemon restart
vandelay daemon status
vandelay daemon logs

# systemctl (Linux)
systemctl --user status vandelay
journalctl --user-unit vandelay --since "1 hour ago"

# Tailscale
tailscale status
tailscale ip -4
sudo tailscale up --ssh

# Vandelay
vandelay tools list --enabled
vandelay tools add <name>
vandelay cron list
vandelay status
```

### Architecture

```
Client Devices
      │
      │  Tailscale (encrypted)
      │
      ▼
┌─────────────────────────────┐
│  VPS                        │
│                             │
│  ┌───────────────────────┐  │
│  │ Tailscale (100.x.x.x) │  │
│  │                       │  │
│  │  ┌─────────────────┐  │  │
│  │  │ Vandelay Agent  │  │  │
│  │  │ FastAPI :8000   │  │  │
│  │  │ WebSocket       │  │  │
│  │  │ Memory + Tools  │  │  │
│  │  └─────────────────┘  │  │
│  │                       │  │
│  └───────────────────────┘  │
│                             │
│  UFW: deny all except       │
│       tailscale0            │
│                             │
│  ┌───────────────────────┐  │
│  │ Tailscale Funnel      │  │  <── Webhooks (public, TLS)
│  │ (only /webhooks/*)    │  │
│  └───────────────────────┘  │
│                             │
└─────────────────────────────┘
      Public IP: all ports closed
```
