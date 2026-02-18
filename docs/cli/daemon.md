# vandelay daemon

Install and manage the background daemon for 24/7 operation.

## Usage

```bash
vandelay daemon <subcommand>
```

## Subcommands

### `install`

Install the daemon as a system service:

```bash
vandelay daemon install
```

- **Linux**: Creates a systemd user unit (`~/.config/systemd/user/vandelay.service`)
- **macOS**: Creates a launchd plist (`~/Library/LaunchAgents/com.vandelay.agent.plist`)
- **Windows**: Not supported (use WSL)

### `uninstall`

Remove the daemon service:

```bash
vandelay daemon uninstall
```

### `start` / `stop` / `restart`

Control the daemon:

```bash
vandelay daemon start
vandelay daemon stop
vandelay daemon restart
```

### `status`

Check if the daemon is running:

```bash
vandelay daemon status
```

### `logs`

View daemon logs:

```bash
vandelay daemon logs
vandelay daemon logs --follow  # Tail logs
```

## How It Works

The daemon runs `vandelay start --no-terminal` as a background service. It:

- Starts the FastAPI server
- Processes messages from all channels
- Runs the scheduler engine for cron jobs and heartbeat
- Restarts automatically if it crashes

## Working Directory

The daemon runs from the user's home directory (`~`), not from `~/.vandelay`. This ensures tools like `shell` and `file` operate relative to the home directory.

## Manual Control

On Linux, you can also manage the daemon directly:

```bash
systemctl --user start vandelay
systemctl --user stop vandelay
systemctl --user restart vandelay
systemctl --user status vandelay
journalctl --user -u vandelay -f  # Tail logs
```
