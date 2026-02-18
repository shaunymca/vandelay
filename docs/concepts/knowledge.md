# Knowledge

Vandelay includes a RAG (Retrieval-Augmented Generation) pipeline for giving your agent access to documents and reference material.

## How It Works

```
Documents → Chunking → Embedding → LanceDB Vector Store
                                        ↓
                              Agent queries knowledge
                                        ↓
                              Relevant chunks returned
                                        ↓
                              Agent uses context in response
```

## Enabling Knowledge

```bash
vandelay config  # → Knowledge → Enable
```

Or in `config.json`:

```json
{
  "knowledge": {
    "enabled": true
  }
}
```

## Embedder Resolution

The embedder is auto-resolved from your model provider:

| Model Provider | Embedder Used | Model |
|---------------|---------------|-------|
| OpenAI | OpenAI Embedder | `text-embedding-3-small` |
| Google | Gemini Embedder | default |
| Ollama | Ollama Embedder | default |
| Anthropic | fastembed (local) | `BAAI/bge-small-en-v1.5` |
| OpenRouter | OpenAI (if key set) or fastembed | varies |

Anthropic has no embedding API, so Vandelay falls back to fastembed — a local embedder that requires no API key.

Override the embedder explicitly in config:

```json
{
  "knowledge": {
    "embedder": {
      "provider": "openai",
      "model": "text-embedding-3-small"
    }
  }
}
```

## Vector Store

Documents are stored in [LanceDB](https://lancedb.github.io/lancedb/) at `~/.vandelay/data/knowledge_vectors/`. LanceDB is embedded (no server needed) and supports fast similarity search.

## CLI Commands

```bash
vandelay knowledge status          # Check knowledge status
vandelay knowledge refresh         # Refresh the corpus
vandelay knowledge refresh --force # Force full rebuild
vandelay knowledge clear --yes     # Clear all knowledge
```

See [CLI Reference: knowledge](../cli/knowledge.md) for full details.
