"""Application lifespan management."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from vandelay.config.constants import CORPUS_VERSIONS_FILE

logger = logging.getLogger("vandelay.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks for vandelay."""
    settings = app.state.settings

    # --- Startup ---
    # Ensure workspace templates exist (restores any missing files)
    from vandelay.workspace.manager import init_workspace
    init_workspace()

    logger.info(
        "Vandelay server starting: agent=%s, host=%s, port=%d",
        settings.agent_name,
        settings.server.host,
        settings.server.port,
    )

    if settings.server.secret_key == "change-me-to-a-random-string":
        logger.warning(
            "Server is using the default secret_key. "
            "Set VANDELAY_SECRET_KEY in ~/.vandelay/.env."
        )

    # Suggest memory migration if needed
    try:
        from vandelay.core.memory_migration import check_migration_needed

        if check_migration_needed(settings):
            logger.info(
                "MEMORY.md has entries that can be migrated to native memory. "
                "Run: vandelay memory migrate"
            )
    except Exception:
        pass  # Non-critical — don't block startup

    # Background corpus indexing (non-blocking).
    # Skip on first run (no corpus_versions.json yet) to avoid a ~130MB
    # download that makes the first launch look hung.  Users can trigger
    # it explicitly with: vandelay knowledge index
    if settings.knowledge.enabled:
        from vandelay.knowledge.corpus import corpus_needs_refresh

        has_been_indexed_before = CORPUS_VERSIONS_FILE.exists()
        if has_been_indexed_before and corpus_needs_refresh():
            knowledge = getattr(app.state, "knowledge", None)
            if knowledge is not None:

                async def _bg_index():
                    from vandelay.knowledge.corpus import index_corpus

                    try:
                        count = await index_corpus(knowledge)
                        logger.info("Corpus indexed: %d URLs", count)
                    except Exception:
                        logger.exception("Corpus indexing failed")

                asyncio.create_task(_bg_index())

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
