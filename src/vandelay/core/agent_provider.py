"""Agent provider abstractions — lazy resolution to fix hot-reload."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentProvider(Protocol):
    """Any callable that returns the *current* Agent or Team instance."""

    def __call__(self) -> Any: ...


class AppStateAgentProvider:
    """Resolves the agent/team from ``app.state.agent`` at call time.

    This ensures hot-reload works: when the reload callback swaps
    ``app.state.agent``, every subsequent call gets the new instance.
    Works for both Agent and Team (duck-type compatible arun interface).
    """

    def __init__(self, app_state: Any) -> None:
        self._app_state = app_state

    def __call__(self) -> Any:
        return self._app_state.agent


class RefAgentProvider:
    """Resolves the agent/team from a mutable ``ref[0]`` list slot.

    Used by the CLI terminal where there is no FastAPI app state.
    """

    def __init__(self, ref: list) -> None:
        self._ref = ref

    def __call__(self) -> Any:
        return self._ref[0]
