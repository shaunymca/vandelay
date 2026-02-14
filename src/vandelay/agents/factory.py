"""Agent factory — creates an Agno Agent from settings."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agno.agent import Agent

from vandelay.agents.prompts.system_prompt import (
    build_personality_brief,
    build_system_prompt,
    build_team_leader_prompt,
)
from vandelay.config.models import MemberConfig
from vandelay.memory.setup import create_db

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)

# Legacy string → tool mapping for backward-compatible member names
_LEGACY_TOOL_MAP: dict[str, list[str]] = {
    "browser": ["crawl4ai", "camofox"],
    "system": ["shell", "file", "python"],
    "scheduler": [],    # uses SchedulerTools injection
    "knowledge": [],    # uses search_knowledge
}

_LEGACY_ROLE_MAP: dict[str, str] = {
    "browser": "Web browsing, scraping, and screenshot specialist",
    "system": "Shell commands, file operations, and package management specialist",
    "scheduler": "Cron jobs, reminders, and recurring task specialist",
    "knowledge": "Document search and RAG query specialist",
}


def _load_env() -> None:
    """Load ~/.vandelay/.env into os.environ so API keys are always available."""
    import os

    from vandelay.config.constants import VANDELAY_HOME

    env_path = VANDELAY_HOME / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # Strip inline comments (e.g. VALUE=foo  # comment)
        if " #" in value:
            value = value[:value.index(" #")]
        value = value.strip()
        # Don't overwrite existing env vars (env vars take priority)
        if key and key not in os.environ:
            os.environ[key] = value


def _get_model_from_config(provider: str, model_id: str, auth_method: str = "api_key"):
    """Instantiate an Agno model class from provider/model_id/auth_method.

    This is the low-level model factory used by both _get_model() (for the main
    agent) and _build_member_agent() (for per-member model overrides).
    """
    import os

    _load_env()

    if provider == "anthropic":
        from agno.models.anthropic import Claude

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


def _get_model(settings: Settings):
    """Instantiate the correct Agno model class from settings."""
    return _get_model_from_config(
        provider=settings.model.provider,
        model_id=settings.model.model_id,
        auth_method=settings.model.auth_method,
    )


def _get_tools(settings: Settings) -> list:
    """Instantiate enabled tools from the tool registry."""
    if not settings.enabled_tools:
        return []

    from vandelay.tools.manager import ToolManager

    manager = ToolManager()
    return manager.instantiate_tools(settings.enabled_tools, settings=settings)


def _resolve_member(member: str | MemberConfig) -> MemberConfig:
    """Normalize a member entry to MemberConfig.

    String members are resolved via legacy lookup maps so that existing configs
    like ``["browser", "system"]`` keep working.
    """
    if isinstance(member, MemberConfig):
        return member

    name = member
    return MemberConfig(
        name=name,
        role=_LEGACY_ROLE_MAP.get(name, ""),
        tools=list(_LEGACY_TOOL_MAP.get(name, [])),
    )


def _load_instructions_file(instructions_file: str) -> str:
    """Load member instructions from file. Returns empty string on failure."""
    if not instructions_file:
        return ""

    from vandelay.config.constants import MEMBERS_DIR

    path = Path(instructions_file)
    # Relative paths resolve against ~/.vandelay/members/
    if not path.is_absolute() and not instructions_file.startswith("~"):
        path = MEMBERS_DIR / path
    else:
        path = Path(path.expanduser())

    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning("Member instructions file not found: %s", path)
        return ""
    except OSError as exc:
        logger.warning("Failed to read member instructions file %s: %s", path, exc)
        return ""


def _build_member_agent(
    mc: MemberConfig,
    *,
    main_model,
    db,
    knowledge,
    settings: Settings,
    personality_brief: str,
    scheduler_engine: object | None = None,
) -> Agent:
    """Create an Agent from a MemberConfig."""
    from vandelay.tools.manager import ToolManager

    # Resolve model: per-member override or inherit main
    if mc.model_provider and mc.model_id:
        model = _get_model_from_config(mc.model_provider, mc.model_id)
    else:
        model = main_model

    # Resolve tools: intersect with enabled_tools so disabled tools aren't used
    tools: list = []
    tool_names = [t for t in mc.tools if t in settings.enabled_tools]
    if tool_names:
        manager = ToolManager()
        tools = manager.instantiate_tools(tool_names, settings=settings)

    # Scheduler member gets SchedulerTools injected
    if mc.name == "scheduler" and scheduler_engine is not None:
        from vandelay.tools.scheduler import SchedulerTools

        tools.append(SchedulerTools(engine=scheduler_engine))

    # Build instructions: tag → personality brief → file contents → inline
    tag = mc.name.upper()
    instructions: list[str] = [
        f"You are the [{tag}] specialist. Always prefix your responses with [{tag}] "
        f"so the user knows which team member is speaking.",
    ]
    if personality_brief:
        instructions.append(personality_brief)

    file_content = _load_instructions_file(mc.instructions_file)
    if file_content:
        instructions.append(file_content)

    instructions.extend(mc.instructions)

    return Agent(
        id=f"vandelay-{mc.name}",
        name=f"{mc.name.title()} Specialist",
        role=mc.role or f"{mc.name.title()} specialist",
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=instructions or None,
        tools=tools or None,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=3,
    )


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
    from vandelay.tools.tool_management import ToolManagementTools
    from vandelay.tools.workspace import WorkspaceTools

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

    # Always include workspace tools for persistent memory management
    tools.append(WorkspaceTools(settings=settings))

    # Include scheduler tools when engine is available
    if scheduler_engine is not None:
        from vandelay.tools.scheduler import SchedulerTools

        tools.append(SchedulerTools(engine=scheduler_engine))

    # Knowledge/RAG
    from vandelay.knowledge.setup import create_knowledge

    knowledge = create_knowledge(settings, db=db)

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
    deep_work_manager: object | None = None,
) -> Any:
    """Build an Agno Team with configurable members for supervisor mode.

    Members can be legacy string names (``"browser"``, ``"system"``, etc.) or
    rich ``MemberConfig`` objects with per-member models and instructions.

    Returns an object duck-type compatible with Agent (same arun interface).
    """
    from agno.team import Team

    from vandelay.knowledge.setup import create_knowledge
    from vandelay.tools.tool_management import ToolManagementTools
    from vandelay.tools.workspace import WorkspaceTools

    db = create_db(settings)
    model = _get_model(settings)
    workspace_dir = Path(settings.workspace_dir)
    instructions = build_team_leader_prompt(
        agent_name=settings.agent_name,
        workspace_dir=workspace_dir,
        settings=settings,
    )
    knowledge = create_knowledge(settings, db=db)
    personality_brief = build_personality_brief(workspace_dir)

    # Build members from config (string or MemberConfig)
    members = []
    for entry in settings.team.members:
        mc = _resolve_member(entry)
        agent = _build_member_agent(
            mc,
            main_model=model,
            db=db,
            knowledge=knowledge,
            settings=settings,
            personality_brief=personality_brief,
            scheduler_engine=scheduler_engine,
        )
        members.append(agent)

    # Supervisor keeps tool management and workspace tools
    tool_mgmt = ToolManagementTools(
        settings=settings,
        reload_callback=reload_callback,
    )
    workspace_tools = WorkspaceTools(settings=settings)
    leader_tools: list = [tool_mgmt, workspace_tools]

    # Deep work tools (when enabled and manager provided)
    if settings.deep_work.enabled and deep_work_manager is not None:
        from vandelay.tools.deep_work import DeepWorkTools

        leader_tools.append(DeepWorkTools(manager=deep_work_manager))

    # Determine respond_directly based on mode
    mode = settings.team.mode
    respond_directly = mode == "route"

    team = Team(
        id="vandelay-team",
        name=settings.agent_name,
        user_id=settings.user_id or "default",
        mode=mode,
        members=members,
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=instructions,
        tools=leader_tools,
        respond_directly=respond_directly,
        update_memory_on_run=True,
        markdown=True,
    )

    return team
