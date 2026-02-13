"""FastAPI application factory with AgentOS integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.os import AgentOS
from fastapi import FastAPI

from vandelay import __version__
from vandelay.agents.factory import create_agent, create_team
from vandelay.channels.router import ChannelRouter
from vandelay.core import AppStateAgentProvider, ChatService
from vandelay.knowledge.setup import create_knowledge
from vandelay.memory.setup import create_db
from vandelay.server.lifespan import lifespan
from vandelay.server.routes.health import health_router
from vandelay.server.routes.ws import ws_router

if TYPE_CHECKING:
    from vandelay.config.settings import Settings

logger = logging.getLogger("vandelay.server")


def create_app(settings: Settings) -> FastAPI:
    """Build the FastAPI application with AgentOS integration.

    1. Creates a base FastAPI app with our custom lifespan
    2. Creates the shared agent and db, stores on app.state
    3. Creates ChatService with lazy AgentProvider (fixes hot-reload)
    4. Registers our custom routes (health, websocket)
    5. Conditionally registers Telegram and WhatsApp channels
    6. Wraps with AgentOS for playground UI and agent management API
    """
    base_app = FastAPI(
        title=f"Vandelay ({settings.agent_name})",
        version=__version__,
        description="Always-on AI assistant powered by Agno",
        lifespan=lifespan,
    )

    # Create scheduler engine (before agent, so tools can be wired)
    from vandelay.scheduler.engine import SchedulerEngine
    from vandelay.scheduler.store import CronJobStore

    # ChatService resolves agent lazily, so we create a temporary provider first
    # and wire the real engine after ChatService exists.
    cron_store = CronJobStore()
    db = create_db(settings)
    knowledge = create_knowledge(settings)

    # Create shared agent/team and db with hot-reload support
    # (scheduler_engine set after ChatService is created below)
    scheduler_engine = None  # forward ref, set after ChatService
    team_mode = settings.team.enabled

    def _build_agent_or_team(**extra_kwargs):
        """Create either an Agent or Team based on settings."""
        if team_mode:
            return create_team(settings, **extra_kwargs)
        return create_agent(settings, **extra_kwargs)

    def _reload_agent() -> None:
        """Recreate the agent/team in-place after tool changes."""
        logger.info("Hot-reloading %s (tool config changed)", "team" if team_mode else "agent")
        new_agent = _build_agent_or_team(
            reload_callback=_reload_agent,
            scheduler_engine=scheduler_engine,
        )
        base_app.state.agent = new_agent
        nonlocal agent
        agent = new_agent

    agent = _build_agent_or_team(reload_callback=_reload_agent)

    # ChatService resolves agent lazily — hot-reload swaps app.state.agent
    # and every subsequent ChatService call picks up the new instance.
    agent_provider = AppStateAgentProvider(base_app.state)
    chat_service = ChatService(agent_provider)

    # Now create the scheduler engine with the real ChatService and
    # recreate the agent/team so it gets SchedulerTools wired in.
    scheduler_engine = SchedulerEngine(settings, chat_service, cron_store)
    agent = _build_agent_or_team(
        reload_callback=_reload_agent,
        scheduler_engine=scheduler_engine,
    )

    # Channel router for managing adapters
    channel_router = ChannelRouter()
    agentos_interfaces = []

    # --- Telegram ---
    if settings.channels.telegram_enabled:
        token = settings.channels.telegram_bot_token
        if token:
            from vandelay.channels.telegram import TelegramAdapter
            from vandelay.server.routes.telegram import telegram_router

            tg_adapter = TelegramAdapter(
                bot_token=token,
                chat_service=chat_service,
                chat_id=settings.channels.telegram_chat_id,
                default_user_id=settings.user_id or "default",
            )
            channel_router.register(tg_adapter)
            base_app.state.telegram_adapter = tg_adapter
            base_app.include_router(telegram_router)
            logger.info("Telegram channel enabled")
        else:
            logger.warning(
                "Telegram enabled but no bot token configured — skipping"
            )

    # --- WhatsApp ---
    if settings.channels.whatsapp_enabled:
        token = settings.channels.whatsapp_access_token
        phone_id = settings.channels.whatsapp_phone_number_id
        if token and phone_id:
            from agno.os.interfaces.whatsapp import Whatsapp

            from vandelay.channels.whatsapp import WhatsAppAdapter

            wa_adapter = WhatsAppAdapter(
                access_token=token,
                phone_number_id=phone_id,
            )
            channel_router.register(wa_adapter)

            # AgentOS Whatsapp interface handles webhooks
            wa_interface = Whatsapp(agent=agent, prefix="/whatsapp")
            agentos_interfaces.append(wa_interface)
            logger.info("WhatsApp channel enabled")
        else:
            logger.warning(
                "WhatsApp enabled but missing access_token or phone_number_id — skipping"
            )

    # Store on app.state for access from route handlers and lifespan
    base_app.state.agent = agent
    base_app.state.settings = settings
    base_app.state.db = db
    base_app.state.channel_router = channel_router
    base_app.state.chat_service = chat_service
    base_app.state.scheduler_engine = scheduler_engine

    # Register our custom routes before AgentOS
    base_app.include_router(health_router)
    base_app.include_router(ws_router)

    # Integrate with AgentOS — adds playground, session,
    # memory, knowledge, and metrics routes automatically.
    agentos_kwargs: dict = dict(
        name=f"vandelay-{settings.agent_name}",
        db=db,
        interfaces=agentos_interfaces or None,
        base_app=base_app,
        on_route_conflict="preserve_base_app",
    )
    if knowledge is not None:
        agentos_kwargs["knowledge"] = [knowledge]
    if team_mode:
        agentos_kwargs["teams"] = [agent]
    else:
        agentos_kwargs["agents"] = [agent]

    agent_os = AgentOS(**agentos_kwargs)

    return agent_os.get_app()
