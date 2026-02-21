# Writing Custom Tools

Vandelay tools are Agno `Toolkit` subclasses. Agents discover tools by reading
their function signatures and docstrings, so the quality of your docstrings
directly affects how well agents use your tool.

## Two Approaches

### `@tool` Decorator — for standalone functions

Best for simple, single-purpose utilities with no shared state.

```python
from agno.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name (e.g. 'New York', 'London').

    Returns:
        A plain-text weather summary.
    """
    # Your implementation here
    return f"Weather in {city}: Sunny, 72°F"
```

### `Toolkit` Subclass — for grouped tools with shared state

Best when several functions share a connection, a browser session, a database
handle, or any resource that should be initialised once and reused.

```python
from agno.tools import Toolkit

class WeatherTools(Toolkit):
    def __init__(self, api_key: str):
        super().__init__(name="weather")
        self.api_key = api_key
        self.register(self.get_weather)
        self.register(self.get_forecast)

    def get_weather(self, city: str) -> str:
        """Get the current weather for a city.

        Args:
            city: The city name.

        Returns:
            A plain-text weather summary.
        """
        return f"Weather in {city}: Sunny, 72°F"

    def get_forecast(self, city: str, days: int = 5) -> str:
        """Get a weather forecast for a city.

        Args:
            city: The city name.
            days: Number of forecast days (default 5).

        Returns:
            A plain-text multi-day forecast.
        """
        return f"{days}-day forecast for {city}: ..."
```

## Critical Rule: Always Use Sync Functions

**Every method you register must be a regular `def`, not `async def`.**

Agno registers sync methods in `Toolkit.functions` and async methods in
`Toolkit.async_functions`. When an agent formats its tool list to send to the
model, it calls `Toolkit.get_functions()` (sync registry only) in the default
path. If you use `async def`, your tools are invisible to the agent.

```python
# ❌ Wrong — functions go into async_functions, invisible to agents
class MyTools(Toolkit):
    async def search(self, query: str) -> str: ...

# ✅ Correct — functions go into functions, always visible
class MyTools(Toolkit):
    def search(self, query: str) -> str: ...
```

If you need to call async code (e.g. an async HTTP client), use
`asyncio.run()` inside the sync function:

```python
import asyncio

def search(self, query: str) -> str:
    """Search the web for a query."""
    return asyncio.run(self._async_search(query))

async def _async_search(self, query: str) -> str:
    async with httpx.AsyncClient() as client:
        ...
```

!!! note "Why this matters"
    Agno's `get_async_functions()` method merges both registries (sync + async),
    so async functions *are* reachable in pure-async paths. But the model tool
    formatting path always uses `get_functions()`. Keeping everything sync
    guarantees visibility everywhere.

## Parameter Types and Docstrings

Agno extracts parameter schemas from Python type annotations at runtime via
`process_entrypoint()`. The agent model receives this schema and uses it to
know which arguments to pass.

**Type annotations are required** — without them, the parameter appears in the
schema with no type and the model may not know how to call it correctly.

**Docstrings drive agent behaviour.** The `Args:` block is parsed and each
parameter description becomes the parameter's `description` in the JSON schema.
Write descriptions as if explaining the parameter to a non-technical colleague.

```python
def book_flight(
    self,
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1,
) -> str:
    """Search for and book a flight.

    Args:
        origin: IATA airport code for the departure airport (e.g. 'JFK').
        destination: IATA airport code for the arrival airport (e.g. 'LHR').
        date: Departure date in YYYY-MM-DD format.
        passengers: Number of adult passengers (default 1).

    Returns:
        Booking confirmation number and flight details.
    """
```

### Supported Parameter Types

| Python type | JSON Schema type |
|-------------|-----------------|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |
| `list[str]` | `array` of `string` |
| `dict` | `object` |
| `Optional[str]` / `str \| None` | `string` (not required) |

## Return Values

**Always return a string.** The agent receives the return value as raw text
and reads it as part of its reasoning. If you return structured data (a dict,
a list), convert it to a readable string first.

```python
# ❌ Wrong — the agent can't read a dict
def get_user(self, user_id: str) -> dict:
    return {"name": "Alice", "email": "alice@example.com"}

# ✅ Correct — readable text
def get_user(self, user_id: str) -> str:
    """Get user details by ID."""
    return "Name: Alice\nEmail: alice@example.com"
```

## Error Handling

Return error messages as strings instead of raising exceptions. If your
function raises, the agent sees the traceback as text — which is confusing.
Return a human-readable error message so the agent can decide what to do.

```python
def read_file(self, path: str) -> str:
    """Read a file and return its contents."""
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"File not found: {path}"
    except PermissionError:
        return f"Permission denied: {path}"
```

## Lazy Initialisation

If your tool opens a browser, database connection, or network session, start
it on first use rather than in `__init__`. This keeps startup fast and lets the
agent decide whether to use the tool at all.

```python
class DatabaseTools(Toolkit):
    def __init__(self, db_url: str):
        super().__init__(name="database")
        self.db_url = db_url
        self._conn = None  # not connected yet
        self.register(self.query)

    def _ensure_connected(self) -> None:
        if self._conn is None:
            import sqlite3
            self._conn = sqlite3.connect(self.db_url)

    def query(self, sql: str) -> str:
        """Run a SQL query and return results as a table.

        Args:
            sql: The SQL query to execute.
        """
        self._ensure_connected()
        cursor = self._conn.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            return "No results."
        headers = [d[0] for d in cursor.description]
        lines = [" | ".join(headers)]
        lines += [" | ".join(str(v) for v in row) for row in rows]
        return "\n".join(lines)
```

## Testing Your Tool

Before wiring a tool into Vandelay, test it in isolation:

```python
# test_my_tool.py
def test_get_weather_returns_string():
    tool = WeatherTools(api_key="test")
    result = tool.get_weather("London")
    assert isinstance(result, str)
    assert "London" in result

def test_functions_are_registered_as_sync():
    """Ensure no async functions slip in — they'd be invisible to agents."""
    tool = WeatherTools(api_key="test")
    assert "get_weather" in tool.functions
    assert "get_forecast" in tool.functions
    assert tool.async_functions == {}

def test_parameter_schema_is_extracted():
    """Verify Agno can extract the parameter schema."""
    tool = WeatherTools(api_key="test")
    func = tool.functions["get_weather"].model_copy(deep=True)
    func.process_entrypoint(strict=False)
    schema = func.to_dict()
    props = schema["parameters"]["properties"]
    assert "city" in props
    assert props["city"]["type"] == "string"
```

Run with `uv run pytest tests/test_my_tool.py -v`.

## Registering with Vandelay

Vandelay discovers tools via its tool registry. The simplest path for a custom
tool is to add it to the manager directly.

!!! warning "Custom tool loading from `~/.vandelay/custom_tools/`"
    Full custom tool loading from a user-space directory is in progress.
    For now, the recommended approach is to add your toolkit to
    `src/vandelay/tools/` and register it in the tool manager.

## Next Steps

- [Built-in Tools](../tools/built-in.md) — examples from Vandelay itself
- [Tool Catalog](../tools/index.md) — 117 tools from Agno's ecosystem
