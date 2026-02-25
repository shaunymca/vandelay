# vandelay update

Pull the latest code, sync dependencies, and restart the daemon.

## Usage

```bash
vandelay update
vandelay update --no-restart  # Skip daemon restart
```

## What It Does

1. Runs `git pull` from the Vandelay repository root
2. Runs `uv sync` to install any new or updated dependencies
3. Restarts the daemon if it is currently running

If the daemon is not running, the restart step is skipped automatically.

## Options

| Flag | Description |
|------|-------------|
| `--no-restart` | Skip daemon restart after update |

## Example Output

```
Pulling latest code from /home/user/vandelay...
  ✓ Already up to date.
Syncing dependencies...
  ✓ Dependencies up to date.
Restarting daemon...
  ✓ Daemon restarted.

Update complete.
```

## Notes

- `vandelay update` must be run from inside the cloned git repository. If Vandelay was not installed from source, it prints a warning and skips the `git pull` step.
- After updating, workspace files in `~/.vandelay/workspace/` are not overwritten — your customizations are preserved. However, if a file is empty, the updated default template is used automatically.
- If `uv sync` fails (e.g. a dependency is unavailable), the update aborts before restarting the daemon to avoid running with partial dependencies.
