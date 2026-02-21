# Building a Full Toolkit

This guide walks through building a production-quality Vandelay toolkit from
scratch, using **CamoufoxTools** — the browser automation toolkit built into
Vandelay — as the worked example. By the end you'll understand:

- How Agno discovers and formats tools for the model
- Why sync vs async functions matters
- How to write parameter schemas that agents understand
- How to test the full pipeline end-to-end

---

## What is CamoufoxTools?

CamoufoxTools wraps [Camoufox](https://github.com/daijro/camoufox) — an
open-source anti-detect Firefox browser with a Playwright API. It gives agents
a persistent browser session with named tabs:

```
open_tab(url)         → opens URL, returns page content
navigate(tab_id, url) → navigate existing tab
get_page_content(tab_id) → full page text / accessibility tree
click(tab_id, selector)  → click an element
type_text(tab_id, selector, text) → fill an input
screenshot(tab_id, path) → save a PNG screenshot
scroll(tab_id, direction) → scroll the page
get_links(tab_id)     → list all links on page
close_tab(tab_id)     → close a tab
list_tabs()           → list all open tabs
```

---

## Step 1: Scaffold the Toolkit

```python
# src/vandelay/tools/camoufox.py

from agno.tools import Toolkit

class CamoufoxTools(Toolkit):
    def __init__(self, headless: bool = True) -> None:
        super().__init__(name="camoufox")
        self._headless = headless
        self._browser = None   # lazy: started on first use
        self._context = None
        self._pages: dict[str, object] = {}
        self._counter = 0

        # Register every public function
        self.register(self.open_tab)
        self.register(self.navigate)
        # ... etc
```

Two things happen here:

1. `super().__init__(name="camoufox")` — the `name` is the slug used in config
   and `enabled_tools` (e.g. `vandelay tools enable camoufox`)
2. `self.register(fn)` — adds the function to `self.functions` (the sync registry)

---

## Step 2: Write Sync Functions

**Every registered function must be a regular `def`.** This is the most common
mistake when writing Agno toolkits.

### Why it matters: How Agno registers tools

Agno's `Toolkit.register()` checks whether the function is a coroutine:

```python
# Agno internals (simplified)
def register(self, fn):
    if asyncio.iscoroutinefunction(fn):
        self.async_functions[fn.__name__] = Function(fn)
    else:
        self.functions[fn.__name__] = Function(fn)
```

### Why it matters: How agents format tools for the model

When an agent prepares its tool list to include in the model request, it calls:

```python
# Agno internals (simplified)
def parse_tools(tools, async_mode=False):
    for tool in tools:
        if isinstance(tool, Toolkit):
            fns = tool.get_async_functions() if async_mode else tool.get_functions()
```

`get_functions()` returns only `self.functions`. `get_async_functions()` returns
`{**self.functions, **self.async_functions}` — sync first, async overrides.

The model's tool formatting path calls `get_functions()` by default. If your
functions are `async def`, they live in `self.async_functions` and are never
forwarded to the model. The agent receives no tools.

### The fix: use sync API + `asyncio.run()` if needed

```python
def open_tab(self, url: str) -> str:
    """Open a new browser tab and navigate to the given URL.

    Args:
        url: The URL to open.

    Returns:
        Tab ID and a text summary of the page content.
    """
    self._ensure_browser()
    page = self._context.new_page()
    tab_id = self._next_tab_id()
    self._pages[tab_id] = page
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    title = page.title()
    text = page.inner_text("body")[:3000].strip()
    return f"Tab {tab_id} opened: {title}\n\n{text}"
```

The Camoufox library ships both sync and async APIs. We use
`camoufox.sync_api.Camoufox` to keep the code straightforward. If you were
wrapping an async library, you'd use `asyncio.run()` inside the sync function.

---

## Step 3: Lazy Browser Initialisation

Starting a browser is expensive — don't do it in `__init__`. Use a
`_ensure_browser()` helper that starts the browser only on first use:

```python
def _ensure_browser(self) -> None:
    """Lazy-start the Camoufox browser on first use."""
    if self._context is not None:
        return                                    # already running

    from camoufox.sync_api import Camoufox       # deferred import

    self._browser = Camoufox(headless=self._headless)
    self._context = self._browser.__enter__()    # sync context manager
```

Benefits:
- Server starts fast even if the agent never uses the browser
- Dependencies are imported only when needed
- Easy to test the toolkit class without a real browser

---

## Step 4: Write Docstrings That Agents Understand

Agno parses your `Args:` blocks to populate the JSON schema's `description`
fields. The model reads these descriptions to know what to pass.

```python
def click(self, tab_id: str, selector: str) -> str:
    """Click an element by CSS selector or text.

    Args:
        tab_id: The tab identifier returned by open_tab (e.g. 'tab1').
        selector: CSS selector or Playwright text selector
                  (e.g. '#submit-btn', 'text=Login', '[data-testid=search]').

    Returns:
        Confirmation message with the page title after the click.
    """
```

When the agent calls `click`, the model knows:
- `tab_id` → the identifier returned by a previous `open_tab` call
- `selector` → a CSS or text selector string, with concrete examples

Bad docstring:
```python
def click(self, tab_id: str, selector: str) -> str:
    """Click."""  # agent has no idea what to pass
```

---

## Step 5: Handle Errors Gracefully

Return error strings, never raise exceptions:

```python
def navigate(self, tab_id: str, url: str) -> str:
    """Navigate an existing tab to a new URL."""
    page = self._pages.get(tab_id)
    if not page:
        return f"Tab {tab_id} not found. Use open_tab() to open a tab first."

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        return f"Navigation failed: {e}"

    return f"Navigated {tab_id} to: {page.title()} ({url})"
```

The agent reads the return value as text. If you return a clear error message,
the agent can recover ("Let me open a tab first"). If you raise, the agent
sees a Python traceback — unreadable and non-actionable.

---

## Step 6: Clean Up Resources

Implement a `close()` method for graceful shutdown. Vandelay calls this during
server shutdown if your toolkit is registered:

```python
def close(self) -> None:
    """Shut down the browser. Called during server shutdown."""
    for page in list(self._pages.values()):
        with contextlib.suppress(Exception):
            page.close()
    self._pages.clear()

    if self._browser is not None:
        with contextlib.suppress(Exception):
            self._browser.__exit__(None, None, None)
        self._browser = None
        self._context = None
```

Use `contextlib.suppress` to swallow errors during teardown — the process is
shutting down anyway and you don't want a cleanup exception to mask the real
reason for shutdown.

---

## Step 7: Test the Full Pipeline

Test three things: registration, parameter schema extraction, and runtime behaviour.

```python
# tests/test_tools/test_camoufox.py
from unittest.mock import MagicMock, patch
from vandelay.tools.camoufox import CamoufoxTools

# --- Registration tests ---

def test_functions_registered_as_sync():
    """All functions must be in self.functions, not async_functions."""
    tool = CamoufoxTools()
    expected = {
        "open_tab", "navigate", "get_page_content", "click",
        "type_text", "screenshot", "scroll", "get_links",
        "close_tab", "list_tabs",
    }
    assert set(tool.functions.keys()) == expected

def test_no_async_functions():
    """async_functions must be empty — async fns are invisible to agents."""
    tool = CamoufoxTools()
    assert tool.async_functions == {}

# --- Schema tests ---

def test_parameter_schema_is_extracted():
    """Agno must be able to extract the full parameter schema."""
    tool = CamoufoxTools()
    func = tool.functions["open_tab"].model_copy(deep=True)
    func.process_entrypoint(strict=False)
    schema = func.to_dict()

    assert schema["name"] == "open_tab"
    props = schema["parameters"]["properties"]
    assert "url" in props
    assert props["url"]["type"] == "string"
    assert "url" in schema["parameters"]["required"]

def test_all_functions_have_parameters():
    """Every function except list_tabs should have typed parameters."""
    tool = CamoufoxTools()
    no_params_allowed = {"list_tabs"}
    for name, func in tool.functions.items():
        f = func.model_copy(deep=True)
        f.process_entrypoint(strict=False)
        schema = f.to_dict()
        props = schema["parameters"].get("properties", {})
        if name not in no_params_allowed:
            assert props, f"{name} has no parameter schema — check type annotations"

# --- Runtime tests ---

def test_list_tabs_empty():
    tool = CamoufoxTools()
    assert tool.list_tabs() == "No open tabs."

def test_navigate_unknown_tab():
    tool = CamoufoxTools()
    result = tool.navigate("tab99", "https://example.com")
    assert "not found" in result

def test_open_tab_launches_browser(mock_camoufox):
    """open_tab should lazy-start the browser and return page content."""
    tool = CamoufoxTools()
    with patch("camoufox.sync_api.Camoufox") as MockCamoufox:
        mock_ctx = MagicMock()
        mock_page = MagicMock()
        mock_page.title.return_value = "Example Domain"
        mock_page.inner_text.return_value = "Example Domain content"
        mock_ctx.new_page.return_value = mock_page
        MockCamoufox.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        MockCamoufox.return_value.__exit__ = MagicMock(return_value=False)

        result = tool.open_tab("https://example.com")

    assert "tab1" in result
    assert "Example Domain" in result
```

Run with:
```bash
uv run pytest tests/test_tools/test_camoufox.py -v
```

---

## Step 8: Register with the Tool Manager

Add your toolkit to `src/vandelay/tools/manager.py`:

```python
# In the TOOL_REGISTRY or equivalent
ToolEntry(
    name="camoufox",
    display_name="Camoufox Browser",
    description="Anti-detect Firefox browser automation via Camoufox + Playwright",
    category="browser",
    class_name="CamoufoxTools",
    module="vandelay.tools.camoufox",
    dependencies=["camoufox[geoip]"],
    is_builtin=True,
)
```

Then enable it:
```bash
vandelay tools enable camoufox
```

Or add it to a member's tools in `~/.vandelay/config.json`:
```json
{
  "name": "cto",
  "tools": ["camoufox", "shell", "file", "python"]
}
```

---

## Debugging Tools Not Working

If an agent says it "can't find" or "doesn't have access to" your tool, check
these in order:

1. **Are functions sync?**
   ```python
   assert tool.async_functions == {}  # must be empty
   assert "my_function" in tool.functions
   ```

2. **Does `process_entrypoint()` extract the schema?**
   ```python
   func = tool.functions["my_function"].model_copy(deep=True)
   func.process_entrypoint(strict=False)
   print(func.to_dict())  # should show parameters
   ```

3. **Does the tool appear in the AgentOS API?**
   ```bash
   curl http://localhost:8000/teams | python -c "
   import sys, json
   teams = json.load(sys.stdin)
   for t in teams:
       for m in t.get('members', []):
           print(m['name'], [fn['name'] for fn in m['tools']['tools'][:5]])
   "
   ```

4. **Check the startup warnings:**
   ```bash
   vandelay daemon logs | grep -i "camoufox\|warning\|error"
   ```
   Errors like `"GOOGLE_AUTH_PORT is not set"` or `"scope gmail.compose required"`
   indicate the tool was skipped at startup.

5. **Are the dependencies installed?**
   ```bash
   uv run python -m camoufox fetch  # downloads GeoIP DB (required)
   uv run python -c "import camoufox; print('ok')"
   ```

---

## Full Source: CamoufoxTools

The complete implementation lives at
[`src/vandelay/tools/camoufox.py`](https://github.com/shaunymca/vandelay/blob/main/src/vandelay/tools/camoufox.py).

Key design decisions:
- Sync API (`camoufox.sync_api`) for full agent visibility
- Named tab dict (`self._pages`) so agents can manage multiple pages
- Accessibility tree snapshot as primary content extraction (falls back to `inner_text`)
- `contextlib.suppress` on all cleanup paths

---

## Next Steps

- [Custom Tools Overview](custom-tool.md) — quick reference
- [Built-in Tools](../tools/built-in.md) — all Vandelay-native toolkits
- [Agent Templates](agent-templates.md) — pre-built agent configs that use these tools
