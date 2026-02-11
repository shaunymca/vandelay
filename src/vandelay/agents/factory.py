"""Agent factory — creates an Agno Agent from settings."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

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

        # Anthropic only supports API keys (no OAuth/token auth)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        return Claude(id=model_id, api_key=api_key) if api_key else Claude(id=model_id)

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

    if provider == "openrouter":
        from agno.models.openai import OpenAIChat

        api_key = os.environ.get("OPENROUTER_API_KEY")
        return OpenAIChat(
            id=model_id,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

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
    scheduler_engine: object | None = None,
) -> Agent:
    """Build the main Agno Agent with memory, storage, and instructions.

    Args:
        settings: Application settings.
        reload_callback: Called by ToolManagementTools after enable/disable
            to trigger an agent hot-reload. If None, a no-op is used.
        scheduler_engine: Optional SchedulerEngine instance. When provided,
            SchedulerTools are added to the agent's toolkit.
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

    # Include scheduler tools when engine is available
    if scheduler_engine is not None:
        from vandelay.tools.scheduler import SchedulerTools

        tools.append(SchedulerTools(engine=scheduler_engine))

    # Knowledge/RAG
    from vandelay.knowledge.setup import create_knowledge

    knowledge = create_knowledge(settings)

    agent = Agent(
        id="vandelay-main",
        name=settings.agent_name,
        user_id=settings.user_id or "default",
        model=model,
        db=db,
        instructions=instructions,
        tools=tools or None,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=5,
        update_memory_on_run=True,
    )

    return agent


def create_team(
    settings: Settings,
    reload_callback: Callable[[], None] | None = None,
    scheduler_engine: object | None = None,
) -> Any:
    """Build an Agno Team with specialist members for supervisor mode.

    The Team wraps specialist agents and routes queries to the right one.
    Falls back to the supervisor (main model) for general queries.

    Returns an object duck-type compatible with Agent (same arun interface).
    """
    from pathlib import Path

    from agno.team import Team

    from vandelay.agents.specialists.agents import SPECIALIST_FACTORIES
    from vandelay.knowledge.setup import create_knowledge
    from vandelay.tools.tool_management import ToolManagementTools

    db = create_db(settings)
    model = _get_model(settings)
    workspace_dir = Path(settings.workspace_dir)
    instructions = build_system_prompt(
        agent_name=settings.agent_name,
        workspace_dir=workspace_dir,
        settings=settings,
    )
    knowledge = create_knowledge(settings)

    # Build specialist members
    members = []
    for member_name in settings.team.members:
        factory = SPECIALIST_FACTORIES.get(member_name)
        if factory is None:
            continue

        kwargs: dict = dict(
            model=model,
            db=db,
            knowledge=knowledge,
            settings=settings,
        )
        # Scheduler specialist needs the engine
        if member_name == "scheduler" and scheduler_engine is not None:
            kwargs["scheduler_engine"] = scheduler_engine

        members.append(factory(**kwargs))

    # Supervisor keeps tool management for enable/disable
    tool_mgmt = ToolManagementTools(
        settings=settings,
        reload_callback=reload_callback,
    )

    team = Team(
        id="vandelay-team",
        name=settings.agent_name,
        mode="coordinate",
        members=members,
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=instructions,
        tools=[tool_mgmt],
        respond_directly=True,
        update_memory_on_run=True,
        markdown=True,
    )

    return team
