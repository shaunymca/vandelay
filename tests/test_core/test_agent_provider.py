"""Tests for AgentProvider implementations."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from vandelay.core.agent_provider import (
    AgentProvider,
    AppStateAgentProvider,
    RefAgentProvider,
)


class TestAppStateAgentProvider:
    def test_resolves_current_agent(self):
        agent_v1 = MagicMock(name="agent_v1")
        app_state = SimpleNamespace(agent=agent_v1)
        provider = AppStateAgentProvider(app_state)

        assert provider() is agent_v1

    def test_resolves_after_hot_reload(self):
        """After hot-reload swaps app.state.agent, provider returns the new one."""
        agent_v1 = MagicMock(name="agent_v1")
        agent_v2 = MagicMock(name="agent_v2")
        app_state = SimpleNamespace(agent=agent_v1)
        provider = AppStateAgentProvider(app_state)

        assert provider() is agent_v1

        # Simulate hot-reload
        app_state.agent = agent_v2
        assert provider() is agent_v2

    def test_satisfies_protocol(self):
        app_state = SimpleNamespace(agent=MagicMock())
        provider = AppStateAgentProvider(app_state)
        assert isinstance(provider, AgentProvider)


class TestRefAgentProvider:
    def test_resolves_current_agent(self):
        agent = MagicMock(name="agent")
        ref = [agent]
        provider = RefAgentProvider(ref)

        assert provider() is agent

    def test_resolves_after_swap(self):
        """After the list slot is swapped, provider returns the new agent."""
        agent_v1 = MagicMock(name="agent_v1")
        agent_v2 = MagicMock(name="agent_v2")
        ref = [agent_v1]
        provider = RefAgentProvider(ref)

        assert provider() is agent_v1

        ref[0] = agent_v2
        assert provider() is agent_v2

    def test_satisfies_protocol(self):
        provider = RefAgentProvider([MagicMock()])
        assert isinstance(provider, AgentProvider)
