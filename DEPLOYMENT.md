# Vandelay Deployment Guide

Vandelay gives your agent shell access, browser control, and persistent memory. That's powerful — and dangerous if exposed to the public internet. This guide covers two deployment paths and the security hardening that makes either one production-ready.

**Rule of thumb:** If someone can reach your Vandelay server, they can tell your agent to run shell commands with your user's permissions. Never expose it without authentication and network isolation.

---

## Table of Contents

- [Choose Your Path](#choose-your-path)
- [Part 1: Local Development](#part-1-local-development)
- [Part 2: Deploy to Railway](#part-2-deploy-to-railway)
- [Part 3: Deploy to a VPS](#part-3-deploy-to-a-vps)
- [Part 4: Secure with Tailscale](#part-4-secure-with-tailscale)
- [Part 5: Expose Webhooks Safely](#part-5-expose-webhooks-safely)
- [Part 6: Harden Everything](#part-6-harden-everything)
- [Part 7: Monitoring & Maintenance](#part-7-monitoring--maintenance)
- [Quick Reference](#quick-reference)

---

## Choose Your Path

| Path | Best For | Cost | Complexity |
|------|----------|------|------------|
| **Railway** | Quick setup, no server management | ~$5-20/mo | Low |
| **VPS + Tailscale** | Full control, maximum security | ~$4-20/mo | Medium |
| **Local only** | Development and testing | Free | None |

**Recommended for production:** VPS + Tailscale. Railway is great for getting started fast, but a VPS with Tailscale gives you full control and zero public attack surface.

---

## Part 1: Local Development

For development and personal use on your own machine. No deployment needed.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An API key from Anthropic, OpenAI, Google, or a local Ollama install

### Setup

```bash
git clone https://github.com/yourusername/vandelay.git
cd vandelay
uv sync
uv run vandelay onboard
uv run vandelay start
```

The onboard wizard walks you through model selection, API keys, safety mode, browser tools, and messaging channels. After setup:

- **Terminal chat** at the console prompt
- **FastAPI server** at `http://localhost:8000`
- **AgentOS playground** at `http://localhost:8000/docs`
- **WebSocket** at `ws://localhost:8000/ws/terminal`

### Verify

```bash
curl http://localhost:8000/health
uv run pytest tests/ -v
```

This is fine for local use — everything binds to `localhost` and never touches the internet. The risk starts when you deploy to a server.

---

## Part 2: Deploy to Railway

Railway is a PaaS that deploys directly from GitHub. No servers to manage, no SSH, no firewall rules. Good for getting Vandelay running quickly.

### 1. Push to GitHub

```bash
git remote add origin https://github.com/yourusername/vandelay.git
git push -u origin master
```

### 2. Create a Railway project

1. Sign in at [railway.app](https://railway.app) with GitHub
2. **New Project** > **Deploy from GitHub repo**
3. Select your Vandelay repository
4. Railway auto-detects Python from `pyproject.toml`

### 3. Set environment variables

In your Railway project, go to **Variables** and add:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `GOOGLE_API_KEY` | Yes* | Google AI API key |
| `VANDELAY_PORT` | Yes | Set to `${{PORT}}` (Railway's dynamic port) |
| `VANDELAY_HOST` | No | Defaults to `0.0.0.0` |
| `VANDELAY_SECRET_KEY` | Recommended | JWT signing key for API auth |
| `TELEGRAM_BOT_TOKEN` | No | For Telegram channel |
| `TELEGRAM_CHAT_ID` | No | Lock bot to one chat |
| `WHATSAPP_ACCESS_TOKEN` | No | For WhatsApp channel |
| `WHATSAPP_PHONE_NUMBER_ID` | No | WhatsApp phone number ID |

*At least one model provider key is required.*

### 4. Configure the start command

In **Settings** > **Deploy** > **Start Command**:

```
vandelay start --server
```

This runs the FastAPI server in headless mode — no terminal chat, just API + WebSocket + webhooks.

### 5. Add persistent storage

Without a volume, your agent's memory and config reset on every deploy.

1. In your Railway project, click **New** > **Volume**
2. Set the mount path to `/root/.vandelay`
3. Attach it to your Vandelay service

This preserves the SQLite database, workspace templates, config, and cron jobs across deployments.

### 6. Custom domain

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

### 9. Ongoing management

| Task | How |
|------|-----|
| **Redeploy** | Push to GitHub — Railway auto-deploys |
| **Logs** | Railway dashboard > **Deployments** > **View Logs** |
| **Add tools** | Railway shell: `vandelay tools add <name>` |
| **Update config** | Change env vars in dashboard — auto-restarts |

### Railway costs

The Hobby plan ($5/month) removes sleep limits so your agent stays on 24/7. The free tier includes $5/month in credits for light use.

### Railway security notes

Railway runs your app in an isolated container, but the FastAPI server is still internet-facing. Anyone who discovers your Railway URL can hit your API endpoints. For serious use:

- Set `VANDELAY_SECRET_KEY` and enforce API authentication
- Use `TELEGRAM_CHAT_ID` to lock your bot to your chat only
- Consider the VPS + Tailscale path below for zero public exposure

---

## Part 3: Deploy to a VPS

A VPS gives you full control. Combined with Tailscale, nothing is internet-facing except what you explicitly allow. This is the recommended production path.

### Recommended providers

| Provider | Spec | Cost |
|----------|------|------|
| **Hetzner** | 2 vCPU, 4GB RAM, 40GB SSD | ~$7/mo |
| **DigitalOcean** | 2 vCPU, 4GB RAM, 80GB SSD | ~$24/mo |
| **AWS Lightsail** | 2 vCPU, 4GB RAM, 80GB SSD | ~$20/mo |

Hetzner offers the best value. Any Ubuntu 22.04+ or Debian 12+ VPS works.

### 1. Provision the server

Create a VPS with your provider. Use SSH key authentication during setup — never password auth.

### 2. Initial server setup

```bash
# SSH in
ssh root@your-server-ip

# Create a non-root user
adduser vandelay
usermod -aG sudo vandelay

# Switch to the new user
su - vandelay
```

### 3. Install dependencies

```bash
# System packages
sudo apt update && sudo apt install -y git curl build-essential

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Install Python 3.11+ (if not already present)
sudo apt install -y python3.11 python3.11-venv
```

### 4. Deploy Vandelay

```bash
# Clone and install
git clone https://github.com/yourusername/vandelay.git ~/vandelay
cd ~/vandelay
uv sync

# Run onboarding
uv run vandelay onboard

# Test it works
uv run vandelay start --server
# Ctrl+C after confirming it starts
```

### 5. Set up systemd

```bash
# Copy the service file
sudo cp ~/vandelay/systemd/vandelay.service /etc/systemd/system/vandelay@.service

# Enable and start
sudo systemctl enable vandelay@vandelay
sudo systemctl start vandelay@vandelay

# Verify
sudo systemctl status vandelay@vandelay
journalctl -u vandelay@vandelay -f
```

The service auto-restarts on failure with a 10-second delay. It runs as your `vandelay` user with systemd hardening (NoNewPrivileges, ProtectSystem).

**Do NOT open ports yet.** The next step locks everything down first.

---

## Part 4: Secure with Tailscale

Tailscale creates an encrypted mesh VPN between your devices. Your Vandelay server gets a private IP (100.x.x.x) that only your authorized devices can reach. Nothing is exposed to the public internet.

### Why Tailscale?

Without Tailscale, your agent's API is one port scan away from discovery. AI agents with shell access are high-value targets — [early deployments of similar tools saw thousands of exposed instances found by Shodan within weeks](https://danlevy.net/securing-clawdbot-tailscale/). Tailscale eliminates this entire attack surface.

### 1. Install Tailscale on your server

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate (opens a browser link)
sudo tailscale up

# Note your Tailscale IP
tailscale ip -4
# Output: 100.x.x.x
```

### 2. Install Tailscale on your devices

Install Tailscale on every device you want to access Vandelay from:
- **Desktop**: [tailscale.com/download](https://tailscale.com/download)
- **Mobile**: App Store / Google Play
- **Other servers**: Same `curl | sh` install as above

All devices on your Tailnet can reach each other. Nothing else can.

### 3. Bind Vandelay to Tailscale only

Set the bind address to your Tailscale IP so the server never listens on the public interface:

```bash
# In ~/.vandelay/.env
VANDELAY_HOST=100.x.x.x    # Your Tailscale IP from step 1
VANDELAY_PORT=8000
```

Restart the service:

```bash
sudo systemctl restart vandelay@vandelay
```

Verify it's only listening on Tailscale:

```bash
sudo ss -tulpn | grep 8000
# Should show 100.x.x.x:8000, NOT 0.0.0.0:8000
```

### 4. Access from your devices

From any device on your Tailnet:

```bash
# Health check
curl http://100.x.x.x:8000/health

# AgentOS playground
open http://100.x.x.x:8000/docs
```

Or use Tailscale's MagicDNS for a friendly hostname:

```bash
curl http://vandelay-server:8000/health
```

### 5. Lock down the firewall

Now that Tailscale is working, block everything else:

```bash
# Default deny all incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow all traffic on the Tailscale interface
sudo ufw allow in on tailscale0

# Enable the firewall
sudo ufw enable

# Verify
sudo ufw status
```

### 6. Verify from outside

From a device NOT on your Tailnet (e.g., your phone on cellular with Tailscale off):

```bash
# This should timeout or be refused
curl http://your-public-ip:8000/health
# Expected: connection refused

# SSH should also be unreachable
ssh vandelay@your-public-ip
# Expected: connection refused
```

From a device ON your Tailnet:

```bash
# This should work
curl http://100.x.x.x:8000/health
# Expected: {"status": "ok"}
```

### 7. Tailscale SSH (optional, recommended)

Replace traditional SSH with Tailscale SSH for keyless, identity-based access:

```bash
# On the server
sudo tailscale up --ssh

# On your client (no keys needed)
ssh vandelay@vandelay-server
```

This eliminates SSH key management entirely. Access is controlled by your Tailscale ACLs.

---

## Part 5: Expose Webhooks Safely

Telegram and WhatsApp require a public HTTPS URL for webhooks. Tailscale Funnel solves this by exposing a single endpoint publicly while keeping everything else private.

### Option A: Tailscale Funnel (recommended)

Funnel exposes one port to the internet through Tailscale's infrastructure, with automatic TLS.

```bash
# Enable HTTPS serving on your Tailscale hostname
sudo tailscale serve --bg https+insecure://localhost:8000

# Expose it publicly via Funnel
sudo tailscale funnel 443 on
```

Your server is now reachable at `https://vandelay-server.your-tailnet.ts.net` — but only on port 443, with TLS, through Tailscale's edge network.

**Set your webhooks:**

```bash
# Telegram
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://vandelay-server.your-tailnet.ts.net/webhooks/telegram"
```

For WhatsApp, set the webhook URL in your Meta Developer Console to:
```
https://vandelay-server.your-tailnet.ts.net/webhooks/whatsapp
```

### Option B: Reverse proxy with nginx

If you prefer a custom domain with traditional TLS:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

```nginx
# /etc/nginx/sites-available/vandelay
server {
    listen 80;
    server_name vandelay.yourdomain.com;

    # Only allow webhook paths publicly
    location /webhooks/ {
        proxy_pass http://100.x.x.x:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Block everything else from public access
    location / {
        return 403;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vandelay /etc/nginx/sites-enabled/
sudo certbot --nginx -d vandelay.yourdomain.com
sudo systemctl reload nginx

# Allow nginx through the firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

This only exposes `/webhooks/*` publicly. The dashboard, API, and WebSocket remain Tailscale-only.

### Option C: No webhooks

If you only use the terminal chat or WebSocket API, skip this entirely. Tailscale is all you need.

---

## Part 6: Harden Everything

### SSH hardening

```bash
sudo nano /etc/ssh/sshd_config
```

Set these values:

```
PasswordAuthentication no
PermitRootLogin no
MaxAuthTries 3
```

If using Tailscale SSH, you can bind SSH to Tailscale only:

```
ListenAddress 100.x.x.x
```

```bash
sudo systemctl restart sshd
```

### File permissions

```bash
# Lock down config and secrets
chmod 700 ~/.vandelay
chmod 600 ~/.vandelay/.env
chmod 600 ~/.vandelay/config.json
chmod 644 ~/.vandelay/data/vandelay.db
```

### Automatic updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Vandelay safety mode

For deployed servers, use **Tiered** or **Confirm** safety mode — never **Trust** on a machine connected to the internet, even through Tailscale:

```bash
# Check current safety mode
uv run vandelay status

# Or change in config
nano ~/.vandelay/config.json
# Set "safety_mode": "tiered"
```

### Database backups

```bash
# Add to crontab: daily backup of SQLite DB
crontab -e
```

```cron
0 3 * * * cp ~/.vandelay/data/vandelay.db ~/.vandelay/data/vandelay.db.bak
```

For PostgreSQL, use `pg_dump` instead.

---

## Part 7: Monitoring & Maintenance

### Check service health

```bash
# Service status
sudo systemctl status vandelay@vandelay

# Live logs
journalctl -u vandelay@vandelay -f

# Health endpoint
curl http://100.x.x.x:8000/health
```

### Update Vandelay

```bash
cd ~/vandelay
git pull
uv sync
sudo systemctl restart vandelay@vandelay
```

### Update Tailscale

```bash
sudo apt update && sudo apt upgrade tailscale
```

### Verify security posture

Run periodically from outside your Tailnet:

```bash
# Should all be unreachable
nmap -p 22,8000 your-public-ip
```

### Check listening ports

```bash
sudo ss -tulpn | grep LISTEN
# Everything should be on 100.x.x.x or 127.0.0.1
# Nothing on 0.0.0.0
```

---

## Quick Reference

### Pre-deployment checklist

- [ ] Tailscale installed and authenticated on server
- [ ] Tailscale installed on all client devices
- [ ] `VANDELAY_HOST` set to Tailscale IP (100.x.x.x)
- [ ] UFW enabled: deny all incoming, allow tailscale0
- [ ] SSH hardened: no password auth, no root login
- [ ] File permissions: `~/.vandelay/` is 700, `.env` is 600
- [ ] Safety mode set to Tiered or Confirm
- [ ] External port scan shows nothing open
- [ ] Webhooks routed through Funnel or nginx (if needed)
- [ ] Automatic OS updates enabled
- [ ] Database backup cron job running

### Common commands

```bash
# Start/stop/restart
sudo systemctl start vandelay@vandelay
sudo systemctl stop vandelay@vandelay
sudo systemctl restart vandelay@vandelay

# Logs
journalctl -u vandelay@vandelay -f
journalctl -u vandelay@vandelay --since "1 hour ago"

# Tailscale
tailscale status              # See connected devices
tailscale ip -4               # Your Tailscale IP
sudo tailscale up --ssh       # Enable Tailscale SSH

# Tools
uv run vandelay tools list --enabled
uv run vandelay tools add <name>
uv run vandelay status
```

### Architecture diagram

```
Your Devices (laptop, phone, tablet)
        │
        │  Tailscale encrypted tunnel
        │
        ▼
┌──────────────────────────────┐
│  VPS (Hetzner/DO/AWS)        │
│                              │
│  ┌────────────────────────┐  │
│  │  Tailscale (100.x.x.x) │  │
│  │                        │  │
│  │  ┌──────────────────┐  │  │
│  │  │  Vandelay Agent  │  │  │
│  │  │  FastAPI :8000   │  │  │
│  │  │  WebSocket       │  │  │
│  │  │  Memory + Tools  │  │  │
│  │  └──────────────────┘  │  │
│  │                        │  │
│  └────────────────────────┘  │
│                              │
│  UFW: deny all except        │
│       tailscale0 interface   │
│                              │
│  ┌────────────────────────┐  │
│  │  Tailscale Funnel      │  │  ◄── Telegram/WhatsApp webhooks
│  │  (only /webhooks/*)    │  │      (public, TLS, limited paths)
│  └────────────────────────┘  │
│                              │
└──────────────────────────────┘
     Public IP: all ports closed
```

---

*Built with [Agno](https://github.com/agno-agi/agno) | Secured with [Tailscale](https://tailscale.com)*
