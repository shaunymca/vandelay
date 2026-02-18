# vandelay memory

View and manage agent memory.

## Usage

```bash
vandelay memory <subcommand>
```

## Subcommands

### `list`

List stored memory records:

```bash
vandelay memory list
```

### `clear`

Clear all memory:

```bash
vandelay memory clear --yes
```

## Memory Types

Vandelay uses multiple memory layers:

- **Session history:** Conversation turns stored per session
- **Agentic memory:** Facts and preferences auto-extracted by Agno
- **Workspace MEMORY.md:** Agent-maintained persistent notes

The `memory` CLI manages the agentic memory records in the SQLite database. Session history and workspace files are managed separately.

See [Memory concept](../concepts/memory.md) for the full memory architecture.
