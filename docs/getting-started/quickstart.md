# Quickstart

Get a running agent in under 5 minutes.

## 1. Onboard

```bash
vandelay onboard
```

The interactive wizard asks three things:

1. **LLM provider:** Pick from 10 providers (Anthropic, OpenAI, Google, Ollama, etc.)
2. **Model:** Fetches available models from your provider in real time
3. **API key:** Stored securely in `~/.vandelay/.env`

This creates your config at `~/.vandelay/config.json` and workspace files at `~/.vandelay/workspace/`.

## 2. Start

```bash
vandelay start
```

This launches the FastAPI server and drops you into a terminal chat session. You're now talking to your agent.

## 3. Try It Out

```
You: What can you do?
You: What tools do you have?
You: Create a cron job that runs every morning at 8am to check the weather
```

## What Just Happened?

- The agent loaded your config, model, and workspace files
- A team supervisor was created (team mode is on by default)
- The Vandelay Expert member joined as your first team specialist
- Memory and session history are being persisted to `~/.vandelay/data/vandelay.db`
- Vandelay provides additional features that [Agno OS](https://os.agno.com), can easily view:
    - **Tracing**: Every agent run, tool call, and model invocation is traced automatically
    - **Knowledge**: RAG pipeline for document search (enable via `vandelay config`)
    - **Chat**: Chat directly with your main agent and explore what it can do
    - **Metrics**: Keep an eye on your token useage
    - **Evaluations**: Measure the quality of your Agent

## Next Steps

- [Enable tools](../cli/tools.md) - Add shell, file, browser, and more
- [Set up Telegram](../guides/telegram-setup.md) - Chat with your agent from your phone
- [Configure your team](../guides/first-team.md) - Add specialist members
- [Deploy to a server](../deployment/index.md) - Run 24/7 on a VPS
