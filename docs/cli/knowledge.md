# vandelay knowledge

Manage the knowledge/RAG corpus.

## Usage

```bash
vandelay knowledge <subcommand>
```

## Subcommands

### `add`

Add a file or directory to the knowledge base:

```bash
vandelay knowledge add ~/docs/report.pdf
vandelay knowledge add ~/my-notes/
```

Supported formats: `.pdf`, `.txt`, `.md`, `.csv`, `.json`, `.docx`, `.doc`

### `status`

Check the current knowledge corpus status:

```bash
vandelay knowledge status
```

Shows: enabled state, embedder provider, document count, vector store path.

### `list`

Show the current vector count and storage path:

```bash
vandelay knowledge list
```

### `refresh`

Re-index the built-in corpus:

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

1. Documents are read from disk (file or directory)
2. Documents are chunked into passages
3. Each chunk is embedded via the configured embedder
4. Vectors are stored in ChromaDB at `~/.vandelay/data/knowledge_vectors/`

The agent queries this vector store when `knowledge.enabled` is `true` and `search_knowledge` is active on the agent.

## Embedder Resolution

See [Knowledge concept](../concepts/knowledge.md) for details on how the embedder is auto-resolved from your model provider.
