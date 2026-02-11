"""Application lifespan management."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

logger = logging.getLogger("vandelay.server")


def _inject_channel_env_vars(settings) -> None:
    """Bridge channel config values into environment variables.

    AgentOS WhatsApp and Telegram tools read credentials from env vars.
    We inject them from config.json so users don't need to set both.
    """
    ch = settings.channels

    # Telegram
    if ch.telegram_enabled and ch.telegram_bot_token:
        os.environ.setdefault("TELEGRAM_TOKEN", ch.telegram_bot_token)

    # WhatsApp
    if ch.whatsapp_enabled:
        if ch.whatsapp_access_token:
            os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", ch.whatsapp_access_token)
        if ch.whatsapp_phone_number_id:
            os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", ch.whatsapp_phone_number_id)
        if ch.whatsapp_verify_token:
            os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", ch.whatsapp_verify_token)
        if ch.whatsapp_app_secret:
            os.environ.setdefault("WHATSAPP_APP_SECRET", ch.whatsapp_app_secret)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks for vandelay."""
    settings = app.state.settings

    # --- Startup ---
    logger.info(
        "Vandelay server starting: agent=%s, host=%s, port=%d",
        settings.agent_name,
        settings.server.host,
        settings.server.port,
    )

    if settings.server.secret_key == "change-me-to-a-random-string":
        logger.warning(
            "Server is using the default secret_key. "
            "Set a strong key in config or via VANDELAY_SERVER__SECRET_KEY."
        )

    # Inject channel credentials into env vars
    _inject_channel_env_vars(settings)

    # Start scheduler engine
    scheduler_engine = getattr(app.state, "scheduler_engine", None)
    if scheduler_engine is not None:
        await scheduler_engine.start()

    # Start all registered channel adapters
    channel_router = getattr(app.state, "channel_router", None)
    if channel_router and channel_router.active_channels:
        logger.info("Starting channels: %s", ", ".join(channel_router.active_channels))
        await channel_router.start_all()

    # Start Camofox browser server if enabled
    camofox_server = None
    if "camofox" in (settings.enabled_tools or []):
        try:
            from vandelay.tools.camofox_server import CamofoxServer
            camofox_server = CamofoxServer()
            if camofox_server.is_installed():
                await camofox_server.start()
                app.state.camofox_server = camofox_server
                logger.info("Camofox browser server started.")
            else:
                logger.warning(
                    "Camofox is enabled but not installed. "
                    "Run: vandelay tools add camofox"
                )
                camofox_server = None
        except Exception:
            logger.exception("Failed to start Camofox server")
            camofox_server = None

    # Start file watcher for auto-restart (opt-in via env var)
    file_watcher = None
    if os.environ.get("VANDELAY_AUTO_RESTART", "").lower() in ("1", "true", "yes"):
        try:
            from pathlib import Path as _Path

            from vandelay.config.constants import CONFIG_FILE, WORKSPACE_DIR
            from vandelay.process.watcher import FileWatcher

            src_dir = _Path(__file__).resolve().parent.parent  # src/vandelay/
            watch_paths = [src_dir, CONFIG_FILE.parent, WORKSPACE_DIR]
            file_watcher = FileWatcher(watch_paths=watch_paths)
            file_watcher.start()
            app.state.file_watcher = file_watcher
            logger.info("Auto-restart file watcher enabled.")
        except Exception:
            logger.exception("Failed to start file watcher")

    app.state.started_at = datetime.now(UTC)

    yield

    # --- Shutdown ---
    # Stop file watcher
    if file_watcher is not None:
        file_watcher.stop()

    # Stop scheduler engine
    if getattr(app.state, "scheduler_engine", None) is not None:
        await app.state.scheduler_engine.stop()

    # Stop Camofox server
    if getattr(app.state, "camofox_server", None) is not None:
        try:
            await app.state.camofox_server.stop()
            logger.info("Camofox server stopped.")
        except Exception:
            logger.exception("Error stopping Camofox server")

    if channel_router and channel_router.active_channels:
        logger.info("Stopping channels...")
        await channel_router.stop_all()

    logger.info("Vandelay server shutting down.")
