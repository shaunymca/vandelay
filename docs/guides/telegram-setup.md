# Telegram Setup

Connect your Vandelay agent to Telegram so you can chat from your phone.

## Step 1: Create a Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a name and username for your bot
4. Copy the **bot token** BotFather gives you

## Step 2: Configure Vandelay

```bash
vandelay config  # → Channels → Telegram → Enable
```

Or add to `~/.vandelay/.env`:

```bash
TELEGRAM_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id    # optional but recommended
```

And in `config.json`:

```json
{
  "channels": {
    "telegram_enabled": true,
    "telegram_chat_id": "123456789"
  }
}
```

## Step 3: Get Your Chat ID

To lock the bot to your chat only (recommended for security):

1. Start a conversation with your bot
2. Send any message
3. Check the server logs — the chat ID will be printed
4. Add it to config as `telegram_chat_id`

## Step 4: Start the Server

```bash
vandelay start
```

The Telegram webhook is automatically registered when the server starts.

## Features

- **Persistent typing** — The bot shows "typing..." while processing (re-sent every 4s)
- **File sending** — The agent can send files via Telegram using `send_file()`
- **Chat lock** — Set `telegram_chat_id` to restrict access to your chat only
- **Shared memory** — Conversations in Telegram share memory with Terminal and other channels

## Troubleshooting

- **Bot not responding**: Check that `telegram_enabled` is `true` and the token is correct
- **Webhook errors**: Ensure your server is publicly accessible (use a reverse proxy or tunnel)
- **"Chat not allowed"**: Verify your `telegram_chat_id` matches the chat you're messaging from
