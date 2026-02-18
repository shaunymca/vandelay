# Troubleshooting

Common issues and how to debug them.

## Agent Not Responding

**Check the daemon is running:**

```bash
vandelay daemon status
systemctl --user status vandelay
```

**Check logs for errors:**

```bash
vandelay daemon logs --follow
journalctl --user -u vandelay -f
```

**Verify config is valid:**

```bash
vandelay config  # Opens the config editor (will show parse errors)
```

## Telegram Bot Not Working

1. **Is Telegram enabled?** Check `channels.telegram_enabled` is `true`
2. **Is the token correct?** Verify `TELEGRAM_TOKEN` in `~/.vandelay/.env`
3. **Is the server publicly accessible?** Telegram needs to reach your webhook URL
4. **Chat ID mismatch?** If `telegram_chat_id` is set, it must match your chat

## Cron Jobs Not Firing

1. **Is the daemon running?** Cron jobs only execute when the server is active
2. **Check the job list:** `vandelay cron list`
3. **Timezone correct?** Cron times are evaluated in the configured timezone
4. **Check logs:** Look for scheduler-related entries in `vandelay daemon logs`

## High Token Usage

- **Reduce history:** Lower `num_history_runs` (default: 2) or `max_tool_calls_from_history` (default: 5)
- **Enable session summaries:** Set `enable_session_summaries: true` to compress old sessions
- **Trim workspace files:** Large `SOUL.md` or `MEMORY.md` files increase every request's token count

## Knowledge/RAG Issues

- **"No embedder available"**: Install fastembed (`uv add fastembed`) or set an explicit embedder provider
- **Empty results**: Run `vandelay knowledge refresh --force` to rebuild the corpus
- **Slow refresh**: Local fastembed depends on CPU speed. Consider using OpenAI embedder for faster processing.

## Memory Issues

- **Agent not remembering**: Check `update_memory_on_run` is enabled (default: true)
- **Wrong channel memory**: Verify all channels use the same `user_id` in config
- **Memory too large**: Use `vandelay memory clear --yes` to reset agentic memory

## Server Won't Start

- **Port in use**: Another process is using port 8000. Change with `VANDELAY_PORT=8001`
- **Missing API key**: Check `~/.vandelay/.env` has your provider's API key
- **Import errors**: Run `uv sync` to install all dependencies

## Getting Help

- Check the [GitHub Issues](https://github.com/shaunymca/vandelay/issues)
- Review the [Configuration Reference](../configuration/index.md) for settings
- Enable debug logging for more verbose output
