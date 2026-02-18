# VPS Deployment

Full walkthrough for deploying Vandelay on an Ubuntu/Debian VPS.

## Prerequisites

- Ubuntu 22.04+ or Debian 12+
- Root or sudo access
- A domain name (optional, for webhooks)

## Step 1: Server Setup

```bash
# Create a dedicated user
sudo adduser vandelay
sudo usermod -aG sudo vandelay
su - vandelay
```

## Step 2: Install Dependencies

```bash
# Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv git

# uv (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

## Step 3: Install Vandelay

```bash
git clone https://github.com/shaunymca/vandelay.git
cd vandelay
uv sync
uv tool install -e .
```

## Step 4: Configure

```bash
vandelay onboard
```

Follow the interactive wizard to set up your model, API key, and initial config.

## Step 5: Install the Daemon

```bash
vandelay daemon install
vandelay daemon start
vandelay daemon status
```

This creates a systemd user unit that:

- Starts Vandelay on boot
- Restarts on failure
- Runs as the `vandelay` user

## Step 6: Reverse Proxy (Nginx)

```bash
sudo apt install nginx
```

Create `/etc/nginx/sites-available/vandelay`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vandelay /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 7: TLS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Step 8: Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Updating

```bash
cd ~/vandelay
git pull
vandelay daemon restart
```

## Monitoring

```bash
vandelay daemon status
vandelay daemon logs --follow
journalctl --user -u vandelay -f
```

## Next Steps

- [Security](security.md) - API key management, JWT, Telegram lock
- [Troubleshooting](troubleshooting.md) - Common issues and debugging
