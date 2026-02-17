# Vandelay Operations Guide

How to update and manage a running Vandelay instance.

---

## Pulling Latest Code

```bash
cd ~/vandelay
git pull origin main
```

## Syncing Dependencies

After pulling, sync dependencies to pick up any new or updated packages:

```bash
uv sync
```

## Restarting the Daemon

After pulling code or changing config, restart the daemon to apply changes:

```bash
systemctl --user restart vandelay
```

## Checking Status

### Daemon status

```bash
systemctl --user status vandelay
```

### Health endpoint

If the server is running, check the health endpoint:

```bash
curl http://localhost:8000/health
```

## Viewing Logs

```bash
journalctl --user -u vandelay -f
```

To see the last 50 lines:

```bash
journalctl --user -u vandelay -n 50
```

## Configuration Changes

Edit `~/.vandelay/config.json` or `~/.vandelay/.env`, then restart the daemon:

```bash
systemctl --user restart vandelay
```

Changes to config require a daemon restart to take effect.
