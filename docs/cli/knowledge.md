# vandelay knowledge

Manage the knowledge/RAG corpus.

## Usage

```bash
vandelay knowledge <subcommand>
```

## Subcommands

### `status`

Check the current knowledge corpus status:

```bash
vandelay knowledge status
```

Shows: enabled state, embedder provider, document count, vector store path.

### `refresh`

Refresh the knowledge corpus:

```bash
vandelay knowledge refresh
vandelay knowledge refresh --force  # Force full rebuild
```

Without `--force`, only re-indexes if source versions have changed.

### `clear`

Clear all knowledge vectors:

```bash
vandelay knowledge clear --yes
```

## How It Works

1. The refresh command downloads/reads source documents
2. Documents are chunked into passages
3. Each chunk is embedded via the configured embedder
4. Vectors are stored in LanceDB at `~/.vandelay/data/knowledge_vectors/`

The agent queries this vector store when `knowledge.enabled` is `true` and `search_knowledge` is active on the agent.

## Embedder Resolution

See [Knowledge concept](../concepts/knowledge.md) for details on how the embedder is auto-resolved from your model provider.
