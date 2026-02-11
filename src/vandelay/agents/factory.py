"""Agent factory — creates an Agno Agent from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from agno.agent import Agent

from vandelay.agents.prompts.system_prompt import build_system_prompt
from vandelay.memory.setup import create_db

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


def _get_model(settings: Settings):
    """Instantiate the correct Agno model class from settings."""
    import os

    provider = settings.model.provider
    model_id = settings.model.model_id
    auth_method = settings.model.auth_method

    if provider == "anthropic":
        from agno.models.anthropic import Claude

        if auth_method == "token":
            token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
            return Claude(id=model_id, auth_token=token)
        return Claude(id=model_id)

    if provider == "openai":
        from agno.models.openai import OpenAIChat

        if auth_method == "token":
            token = os.environ.get("OPENAI_AUTH_TOKEN")
            return OpenAIChat(id=model_id, api_key=token)
        return OpenAIChat(id=model_id)

    if provider == "google":
        from agno.models.google import Gemini

        return Gemini(id=model_id)

    if provider == "ollama":
        from agno.models.ollama import Ollama

        return Ollama(id=model_id)

    raise ValueError(f"Unknown model provider: {provider}")


def _get_tools(settings: Settings) -> list:
    """Instantiate enabled tools from the tool registry."""
    if not settings.enabled_tools:
        return []

    from vandelay.tools.manager import ToolManager

    manager = ToolManager()
    return manager.instantiate_tools(settings.enabled_tools, settings=settings)


def create_agent(
    settings: Settings,
    reload_callback: Callable[[], None] | None = None,
) -> Agent:
    """Build the main Agno Agent with memory, storage, and instructions.

    Args:
        settings: Application settings.
        reload_callback: Called by ToolManagementTools after enable/disable
            to trigger an agent hot-reload. If None, a no-op is used.
    """
    from pathlib import Path

    from vandelay.tools.tool_management import ToolManagementTools

    db = create_db(settings)
    model = _get_model(settings)
    workspace_dir = Path(settings.workspace_dir)
    instructions = build_system_prompt(
        agent_name=settings.agent_name,
        workspace_dir=workspace_dir,
        settings=settings,
    )
    tools = _get_tools(settings)

    # Always include the tool management toolkit
    tool_mgmt = ToolManagementTools(
        settings=settings,
        reload_callback=reload_callback,
    )
    tools.append(tool_mgmt)

    agent = Agent(
        id="vandelay-main",
        name=settings.agent_name,
        user_id=settings.user_id or "default",
        model=model,
        db=db,
        instructions=instructions,
        tools=tools or None,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=5,
        update_memory_on_run=True,
    )

    return agent
