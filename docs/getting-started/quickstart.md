# Quickstart

Get a running agent in under 5 minutes.

## 1. Open the Dashboard

```bash
vandelay
```

This opens the Vandelay TUI dashboard. On first launch, the onboarding wizard appears automatically and walks you through 5 steps:

1. **Agent name:** What to call your agent
2. **LLM provider:** Pick from 10 providers (Anthropic, OpenAI, Google, Ollama, etc.)
3. **API key / Auth:** Stored securely in `~/.vandelay/.env` (skipped for Ollama; OpenAI subscription uses OAuth)
4. **Model:** Select the specific model to use (curated list per provider)
5. **Timezone:** For scheduling and cron jobs

Your config is saved to `~/.vandelay/config.json` and workspace files are created at `~/.vandelay/workspace/`.

## 2. Start the Server

Open a second terminal and start the agent server:

```bash
vandelay start
```

This launches the FastAPI server and connects it to your agent. The TUI's Chat tab will show a green dot once connected.

For 24/7 operation, install the daemon instead:

```bash
vandelay daemon install
vandelay daemon start
```

## 3. Chat

Back in the TUI, the **Chat** tab is your primary interface. Try:

```
What can you do?
What tools do you have?
Create a cron job that runs every morning at 8am to check the weather
```

## What Just Happened?

- The agent loaded your config, model, and workspace files
- Memory and session history are being persisted to `~/.vandelay/data/vandelay.db`
- Vandelay provides additional features that [Agno OS](https://os.agno.com) can easily view:
    - **Tracing**: Every agent run, tool call, and model invocation is traced automatically
    - **Knowledge**: RAG pipeline for document search (enable via `vandelay config`)
    - **Chat**: Chat directly with your main agent and explore what it can do
    - **Metrics**: Keep an eye on your token usage
    - **Evaluations**: Measure the quality of your agent

## Next Steps

- [Enable tools](../cli/tools.md) - Add shell, file, browser, and more
- [Set up Telegram](../guides/telegram-setup.md) - Chat with your agent from your phone
- [Configure your team](../guides/first-team.md) - Add specialist members
- [Deploy to a server](../deployment/index.md) - Run 24/7 on a VPS
