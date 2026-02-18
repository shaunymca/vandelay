# Custom Tools

Build your own tools for Vandelay agents using Agno's toolkit system.

## Two Approaches

### 1. `@tool` Decorator (Simple)

For standalone functions:

```python
from agno.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # Your implementation here
    return f"Weather in {city}: Sunny, 72°F"
```

### 2. `Toolkit` Subclass (Full Control)

For grouped tools with shared state:

```python
from agno.tools import Toolkit

class WeatherTools(Toolkit):
    def __init__(self, api_key: str):
        super().__init__(name="weather")
        self.api_key = api_key
        self.register(self.get_weather)
        self.register(self.get_forecast)

    def get_weather(self, city: str) -> str:
        """Get the current weather for a city."""
        return f"Weather in {city}: Sunny, 72°F"

    def get_forecast(self, city: str, days: int = 5) -> str:
        """Get a weather forecast for a city."""
        return f"{days}-day forecast for {city}: ..."
```

## Registering Custom Tools

<!-- TODO: Document custom tool registration via ~/.vandelay/custom_tools/ -->
<!-- TODO: Document the tool factory and vandelay expert workflow -->

Custom tools are placed in `~/.vandelay/custom_tools/` and registered via the tool registry.

## Assigning to Members

Once registered, assign tools to team members:

```json
{
  "team": {
    "members": [
      {
        "name": "weather-bot",
        "role": "Weather specialist",
        "tools": ["weather"]
      }
    ]
  }
}
```

## Best Practices

- Keep tool functions focused: one action per function
- Write clear docstrings: the agent uses them to understand when to call the tool
- Return strings: the agent reads the return value as text
- Handle errors gracefully: return error messages, don't raise exceptions
- Use type hints: they help the agent understand parameter types

## Next Steps

- [Tool Catalog](../tools/index.md) - Browse available tools
- [Built-in Tools](../tools/built-in.md) - See Vandelay's custom toolkits
