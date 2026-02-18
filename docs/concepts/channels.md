# Channels

Vandelay is channel-agnostic: the same agent handles messages from any source with shared memory and context.

## Supported Channels

| Channel | Interface | Setup |
|---------|-----------|-------|
| **Terminal** | CLI chat session | Built-in, always available |
| **Telegram** | Bot via BotFather | [Telegram Setup guide](../guides/telegram-setup.md) |
| **WhatsApp - Untsted** | Cloud API webhook | Config + Meta developer account |
| **WebSocket** | Real-time connection | Built-in, available at `/ws` |

## How It Works

All channels route through `ChatService.run()`:

```
Terminal Input  ─┐
Telegram Webhook ─┤→ ChatService.run() → Agent/Team → Response
WhatsApp Webhook ─┤
WebSocket Message ┘
```

The `ChatService` normalizes incoming messages into a common format, passes them to the agent, and routes responses back through the originating channel.

## Shared Memory

All channels use the same `user_id` from config. This means:

- Conversations in Telegram are visible from Terminal
- Memory persists across channel switches
- The agent maintains one continuous context

## Channel-Specific Features

### Terminal
- Interactive REPL with Rich markdown rendering
- File paths auto-resolved

### Telegram
- Persistent typing indicator (re-sent every 4s during processing)
- File sending via `send_file()` tool
- Chat lock by `telegram_chat_id` for security

### WhatsApp
- Webhook verification with Meta app secret
- Message signature validation

### WebSocket
- Real-time streaming
- Used by the FastAPI server's built-in web interface
