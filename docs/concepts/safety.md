# Safety

Vandelay includes a safety system for shell command execution. Since the agent has system access, guardrails prevent accidental damage.

## Safety Modes

| Mode | Behavior |
|------|----------|
| `trust` | All commands auto-approved. Use only on isolated servers. |
| `confirm` | Every shell command requires user approval before execution. |
| `tiered` | Safe commands auto-approved, risky commands require confirmation. (Default) |

Configure in `config.json`:

```json
{
  "safety": {
    "mode": "tiered"
  }
}
```

## Tiered Mode

In `tiered` mode, commands are classified:

### Auto-Approved (safe)

Commands in the `allowed_commands` list run without confirmation:

```
ls, cat, head, tail, grep, find, echo, pwd, whoami, date, ...
```

### Requires Confirmation (risky)

Any command not in the allowed list prompts for approval.

### Blocked (dangerous)

Commands matching `blocked_patterns` are rejected outright:

```
rm -rf /, mkfs, dd if=, :(){ :|:& };:, ...
```

## Command Timeout

All shell commands have a configurable timeout (default: 120 seconds):

```json
{
  "safety": {
    "command_timeout_seconds": 120
  }
}
```

## File Write Protection

The `FileTools` toolkit includes a write allowlist. By default, writes to `src/vandelay/` (the source code) are blocked to prevent the agent from modifying its own code.

## Best Practices

- Use `tiered` mode for most deployments
- Use `trust` mode only on dedicated, isolated servers
- Lock Telegram to a single `chat_id` to prevent unauthorized access
- Store secrets in `~/.vandelay/.env`, never in `config.json`
- Use a strong `VANDELAY_SECRET_KEY` for JWT signing
