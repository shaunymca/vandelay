"""Specialist agent factories for team supervisor mode.

Each factory creates a focused Agent with a subset of tools and a role prompt.
All specialists share the same model, db, and knowledge as the main agent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from agno.agent import Agent

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


def create_browser_agent(
    *,
    model: Any,
    db: Any,
    knowledge: Any,
    settings: Settings,
) -> Agent:
    """Specialist for web browsing, scraping, and screenshots."""
    from vandelay.tools.manager import ToolManager

    browser_tool_names = [t for t in settings.enabled_tools if t in ("crawl4ai", "camofox")]
    tools = []
    if browser_tool_names:
        manager = ToolManager()
        tools = manager.instantiate_tools(browser_tool_names, settings=settings)

    return Agent(
        id="vandelay-browser",
        name="Browser Specialist",
        role="Web browsing, scraping, and screenshot specialist",
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=[
            "You are the browser specialist. Your job is to browse the web, "
            "scrape content, take screenshots, and extract information from websites.",
            "Use your browsing tools to fulfill requests about web content.",
        ],
        tools=tools or None,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=3,
    )


def create_system_agent(
    *,
    model: Any,
    db: Any,
    knowledge: Any,
    settings: Settings,
) -> Agent:
    """Specialist for shell commands, file operations, and package management."""
    from vandelay.tools.manager import ToolManager

    system_tool_names = [t for t in settings.enabled_tools if t in ("shell", "file", "python")]
    tools = []
    if system_tool_names:
        manager = ToolManager()
        tools = manager.instantiate_tools(system_tool_names, settings=settings)

    return Agent(
        id="vandelay-system",
        name="System Specialist",
        role="Shell commands, file operations, and package management specialist",
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=[
            "You are the system specialist. Your job is to execute shell commands, "
            "manage files, install packages, and perform system operations.",
            "Always consider safety when executing commands.",
        ],
        tools=tools or None,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=3,
    )


def create_scheduler_agent(
    *,
    model: Any,
    db: Any,
    knowledge: Any,
    settings: Settings,
    scheduler_engine: Any | None = None,
) -> Agent:
    """Specialist for cron jobs, reminders, and recurring tasks."""
    tools = []
    if scheduler_engine is not None:
        from vandelay.tools.scheduler import SchedulerTools

        tools.append(SchedulerTools(engine=scheduler_engine))

    return Agent(
        id="vandelay-scheduler",
        name="Scheduler Specialist",
        role="Cron jobs, reminders, and recurring task specialist",
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=[
            "You are the scheduler specialist. Your job is to manage cron jobs, "
            "set reminders, and handle recurring tasks.",
            "Use your scheduler tools to create, list, pause, resume, and delete jobs.",
        ],
        tools=tools or None,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=3,
    )


def create_knowledge_agent(
    *,
    model: Any,
    db: Any,
    knowledge: Any,
    settings: Settings,
) -> Agent:
    """Specialist for document search and RAG queries."""
    return Agent(
        id="vandelay-knowledge",
        name="Knowledge Specialist",
        role="Document search and RAG query specialist",
        model=model,
        db=db,
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=[
            "You are the knowledge specialist. Your job is to search through "
            "the knowledge base, answer questions from documents, and provide "
            "information from the RAG system.",
            "Always cite which documents your answers come from when possible.",
        ],
        markdown=True,
        add_history_to_context=True,
        num_history_runs=3,
    )


# Registry of all specialist factories
SPECIALIST_FACTORIES: dict[str, Callable[..., Agent]] = {
    "browser": create_browser_agent,
    "system": create_system_agent,
    "scheduler": create_scheduler_agent,
    "knowledge": create_knowledge_agent,
}
