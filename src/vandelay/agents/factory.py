"""Agent factory — creates an Agno Agent from settings."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agno.agent import Agent

from vandelay.agents.prompts.system_prompt import (
    build_system_prompt,
    build_team_leader_prompt,
)
from vandelay.config.models import MemberConfig
from vandelay.memory.setup import create_db

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger(__name__)

# Named presets: maps known member names to their default tools and roles
_PRESET_TOOL_MAP: dict[str, list[str]] = {
    "vandelay-expert": ["file", "python", "shell"],
}

_PRESET_ROLE_MAP: dict[str, str] = {
    "vandelay-expert": (
        "Agent builder — designs, creates, tests, and improves team member agents"
    ),
}


def _get_codex_token() -> str | None:
    """Read the ChatGPT Plus/Pro access token from ~/.codex/auth.json.

    Auto-refreshes using the stored refresh_token if the access token has
    expired or is within 60 seconds of expiring.
    """
    import base64
    import json
    import time
    import urllib.parse
    import urllib.request
    from datetime import datetime, timezone
    from pathlib import Path

    codex_auth = Path.home() / ".codex" / "auth.json"
    if not codex_auth.exists():
        logger.warning("~/.codex/auth.json not found — run `codex login` first")
        return None

    try:
        data = json.loads(codex_auth.read_text(encoding="utf-8"))
        tokens = data.get("tokens", {})
        access_token = tokens.get("access_token")
        if not access_token:
            return None

        # Decode JWT exp claim (no signature verification needed here)
        payload = access_token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        exp = claims.get("exp", 0)

        if exp > time.time() + 60:
            return access_token

        # Token expired or expiring soon — refresh it
        refresh_token = tokens.get("refresh_token")
        client_id = claims.get("client_id", "app_EMoamEEZ73f0CkXaXp7hrann")
        if not refresh_token:
            logger.warning("Codex access token expired and no refresh_token available")
            return access_token  # try anyway

        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }).encode()
        req = urllib.request.Request(
            "https://auth.openai.com/oauth/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())

        if "access_token" not in result:
            logger.warning("Codex token refresh returned no access_token")
            return access_token

        data["tokens"]["access_token"] = result["access_token"]
        if "refresh_token" in result:
            data["tokens"]["refresh_token"] = result["refresh_token"]
        data["last_refresh"] = datetime.now(timezone.utc).isoformat()
        codex_auth.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Codex token refreshed and saved to ~/.codex/auth.json")
        return result["access_token"]

    except Exception as exc:
        logger.warning("Failed to read/refresh Codex token: %s", exc)
        return None


def _load_env() -> None:
    """Load ~/.vandelay/.env into os.environ so API keys are always available."""
    import os

    from vandelay.config.constants import VANDELAY_HOME

    # Suppress noisy HuggingFace symlink warning on Windows
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

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

        if auth_method == "codex":
            token = _get_codex_token()
            return OpenAIChat(id=model_id, api_key=token) if token else OpenAIChat(id=model_id)
        return OpenAIChat(id=model_id)

    if provider == "google":
        from agno.models.google import Gemini

        return Gemini(id=model_id)

    if provider == "ollama":
        from agno.models.ollama import Ollama

        return Ollama(id=model_id)

    if provider == "groq":
        from agno.models.groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        return Groq(id=model_id, api_key=api_key) if api_key else Groq(id=model_id)

    if provider == "deepseek":
        from agno.models.deepseek import DeepSeek

        api_key = os.environ.get("DEEPSEEK_API_KEY")
        return DeepSeek(id=model_id, api_key=api_key) if api_key else DeepSeek(id=model_id)

    if provider == "mistral":
        from agno.models.mistral import MistralChat

        api_key = os.environ.get("MISTRAL_API_KEY")
        return MistralChat(id=model_id, api_key=api_key) if api_key else MistralChat(id=model_id)

    if provider == "together":
        from agno.models.together import Together

        api_key = os.environ.get("TOGETHER_API_KEY")
        return Together(id=model_id, api_key=api_key) if api_key else Together(id=model_id)

    if provider == "xai":
        from agno.models.xai import xAI

        api_key = os.environ.get("XAI_API_KEY")
        return xAI(id=model_id, api_key=api_key) if api_key else xAI(id=model_id)

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


def _ensure_template_instructions(mc: MemberConfig) -> MemberConfig:
    """Copy starter template to members dir if not already present."""
    from vandelay.agents.templates import STARTER_TEMPLATES, get_template_content
    from vandelay.config.constants import MEMBERS_DIR

    if mc.instructions_file:
        return mc  # Already has custom instructions

    template = STARTER_TEMPLATES.get(mc.name)
    if template is None:
        return mc  # Not a known template

    instructions_path = MEMBERS_DIR / f"{mc.name}.md"
    if not instructions_path.exists():
        try:
            MEMBERS_DIR.mkdir(parents=True, exist_ok=True)
            content = get_template_content(template.slug)
            instructions_path.write_text(content, encoding="utf-8")
            logger.info("Bootstrapped template: %s", instructions_path)
        except Exception:
            logger.warning("Failed to bootstrap template for %s", mc.name)
            return mc

    mc.instructions_file = f"{mc.name}.md"
    return mc


def _resolve_member(member: str | MemberConfig) -> MemberConfig:
    """Normalize a member entry to MemberConfig.

    String members are resolved via legacy lookup maps so that existing configs
    like ``["browser", "system"]`` keep working.
    """
    if isinstance(member, MemberConfig):
        return member

    name = member
    mc = MemberConfig(
        name=name,
        role=_PRESET_ROLE_MAP.get(name, ""),
        tools=list(_PRESET_TOOL_MAP.get(name, [])),
    )

    # Auto-bootstrap template instructions if available
    mc = _ensure_template_instructions(mc)
    return mc


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
    extra_tools: list | None = None,
    scheduler_engine: object | None = None,
    task_store: object | None = None,
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

    # All members get task queue tools
    if task_store is not None:
        from vandelay.tools.tasks import TaskQueueTools

        tools.append(TaskQueueTools(store=task_store))

    # All members can request tools from the leader
    from vandelay.tools.tool_request import ToolRequestTools

    tools.append(ToolRequestTools(settings=settings, member_name=mc.name))

    # Inject any caller-provided extra tools (e.g., KnowledgeManagementTools for vandelay-expert)
    if extra_tools:
        tools.extend(extra_tools)

    # Build instructions: tag → tool awareness → file contents → inline
    tag = mc.name.upper()
    instructions: list[str] = [
        f"You are the [{tag}] specialist. Always prefix your responses with [{tag}] "
        f"so the user knows which team member is speaking.",
    ]

    # Tool awareness: tell the member exactly what tools it has
    if tool_names:
        tools_str = ", ".join(tool_names)
        instructions.append(
            f"Your available tools: {tools_str}. "
            "Their full method signatures are already in your function "
            "definitions. Call them directly — NEVER read source code, "
            "run shell commands to inspect packages, or write Python "
            "scripts to replicate what a tool already does. "
            "If a task requires a tool you don't have, call "
            "request_tool(tool_name, reason) to ask the leader for it."
        )

    file_content = _load_instructions_file(mc.instructions_file)
    if file_content:
        instructions.append(file_content)

    instructions.extend(mc.instructions)

    return Agent(
        id=f"vandelay-{mc.name}",
        name=f"{mc.name.title()} Specialist",
        role=mc.role or f"{mc.name.title()} specialist",
        user_id=f"member_{mc.name}",
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=instructions or None,
        tools=tools or None,
        markdown=False,
        add_history_to_context=True,
        num_history_runs=2,
        max_tool_calls_from_history=3,
        enable_session_summaries=True,
        update_memory_on_run=True,
    )


def create_agent(
    settings: Settings,
    reload_callback: Callable[[], None] | None = None,
    scheduler_engine: object | None = None,
    task_store: object | None = None,
    channel_router: object | None = None,
) -> Agent:
    """Build the main Agno Agent with memory, storage, and instructions.

    Args:
        settings: Application settings.
        reload_callback: Called by ToolManagementTools after enable/disable
            to trigger an agent hot-reload. If None, a no-op is used.
        scheduler_engine: Optional SchedulerEngine instance. When provided,
            SchedulerTools are added to the agent's toolkit.
        task_store: Optional TaskStore instance. When provided,
            TaskQueueTools are added to the agent's toolkit.
        channel_router: Optional ChannelRouter instance. When provided,
            NotifyTools are added so the agent can send proactive messages.
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
    tools.append(WorkspaceTools(settings=settings, db=db))

    # Include scheduler tools when engine is available
    if scheduler_engine is not None:
        from vandelay.tools.scheduler import SchedulerTools

        tools.append(SchedulerTools(engine=scheduler_engine, default_timezone=settings.timezone))

    # Include task queue tools when store is available
    if task_store is not None:
        from vandelay.tools.tasks import TaskQueueTools

        tools.append(TaskQueueTools(store=task_store))

    # Proactive notification tools when channel router is available
    if channel_router is not None:
        from vandelay.tools.notify import NotifyTools

        tools.append(NotifyTools(channel_router=channel_router))

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
        num_history_runs=2,
        max_tool_calls_from_history=5,
        enable_session_summaries=True,
        update_memory_on_run=True,
    )

    return agent


def create_team(
    settings: Settings,
    reload_callback: Callable[[], None] | None = None,
    scheduler_engine: object | None = None,
    deep_work_manager: object | None = None,
    task_store: object | None = None,
    channel_router: object | None = None,
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

    # Build members from config (string or MemberConfig)
    members = []
    for entry in settings.team.members:
        mc = _resolve_member(entry)

        # Each member gets its own isolated knowledge collection (if enabled)
        if mc.knowledge_enabled:
            member_knowledge = create_knowledge(settings, db=db, member_name=mc.name)
        else:
            member_knowledge = None

        # Vandelay Expert gets KnowledgeManagementTools so it can manage
        # knowledge bases for any team member via natural language
        extra_tools: list = []
        if mc.name == "vandelay-expert" and settings.knowledge.enabled:
            from vandelay.tools.knowledge_management import KnowledgeManagementTools

            extra_tools.append(KnowledgeManagementTools(settings=settings, db=db))

        agent = _build_member_agent(
            mc,
            main_model=model,
            db=db,
            knowledge=member_knowledge,
            extra_tools=extra_tools,
            settings=settings,
            scheduler_engine=scheduler_engine,
            task_store=task_store,
        )
        members.append(agent)

    # Supervisor keeps tool management and workspace tools
    tool_mgmt = ToolManagementTools(
        settings=settings,
        reload_callback=reload_callback,
    )
    workspace_tools = WorkspaceTools(settings=settings, db=db)
    leader_tools: list = [tool_mgmt, workspace_tools]

    # Member management tools for the leader
    from vandelay.tools.member_management import MemberManagementTools

    leader_tools.append(MemberManagementTools(
        settings=settings,
        reload_callback=reload_callback,
    ))

    # Task queue tools for the leader
    if task_store is not None:
        from vandelay.tools.tasks import TaskQueueTools

        leader_tools.append(TaskQueueTools(store=task_store))

    # Deep work tools (when enabled and manager provided)
    if settings.deep_work.enabled and deep_work_manager is not None:
        from vandelay.tools.deep_work import DeepWorkTools

        leader_tools.append(DeepWorkTools(manager=deep_work_manager))

    # Proactive notification tools for the leader
    if channel_router is not None:
        from vandelay.tools.notify import NotifyTools

        leader_tools.append(NotifyTools(channel_router=channel_router))

    # Scheduler tools so the leader can create/manage cron jobs directly
    if scheduler_engine is not None:
        from vandelay.tools.scheduler import SchedulerTools

        leader_tools.append(SchedulerTools(engine=scheduler_engine, default_timezone=settings.timezone))

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
        add_history_to_context=True,
        num_history_runs=2,
        max_tool_calls_from_history=5,
        enable_session_summaries=True,
        markdown=True,
    )

    return team
