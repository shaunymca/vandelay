# Security

Best practices for securing your Vandelay deployment.

## API Key Management

**Never put API keys in `config.json`.** Use `~/.vandelay/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_TOKEN=123456:ABC...
VANDELAY_SECRET_KEY=your-random-secret
```

Vandelay automatically migrates secrets found in `config.json` to `.env` on startup.

### File Permissions

```bash
chmod 600 ~/.vandelay/.env
chmod 700 ~/.vandelay/
```

## JWT Secret

The server uses a JWT secret for WebSocket authentication. **Change the default**:

```bash
# Generate a strong secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to `~/.vandelay/.env`:

```bash
VANDELAY_SECRET_KEY=your-generated-secret
```

## Telegram Chat Lock

Lock your Telegram bot to a single chat ID to prevent unauthorized access:

```json
{
  "channels": {
    "telegram_enabled": true,
    "telegram_chat_id": "123456789"
  }
}
```

Without this, anyone who finds your bot can chat with it.

## Safety Modes

For production servers:

- **`tiered`** (recommended): Auto-approves safe commands, blocks dangerous ones, confirms everything else
- **`trust`**: Only use on isolated, dedicated servers where the agent needs full autonomy

```json
{
  "safety": {
    "mode": "tiered"
  }
}
```

## Network Security

- **Bind to localhost** if using a reverse proxy: set `"host": "127.0.0.1"` in server config
- **Use TLS** via Nginx + Let's Encrypt (see [VPS guide](vps.md))
- **Firewall:** Only expose ports 22, 80, 443

## File Write Protection

The `FileTools` toolkit blocks writes to `src/vandelay/` by default, preventing the agent from modifying its own source code. Custom blocked paths can be configured.

## Checklist

- [ ] API keys in `.env`, not `config.json`
- [ ] Strong `VANDELAY_SECRET_KEY`
- [ ] Telegram `chat_id` set
- [ ] Safety mode set to `tiered` or higher
- [ ] `.env` file permissions: `600`
- [ ] Nginx with TLS in front of the server
- [ ] Firewall enabled (UFW or equivalent)
- [ ] Server binds to `127.0.0.1` (behind proxy)
