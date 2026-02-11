"""Telegram webhook route — receives updates from Telegram Bot API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

logger = logging.getLogger("vandelay.server.telegram")

telegram_router = APIRouter(prefix="/telegram", tags=["Telegram"])


@telegram_router.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """Receive a Telegram Update and delegate to TelegramAdapter."""
    adapter = getattr(request.app.state, "telegram_adapter", None)
    if adapter is None:
        return Response(content="Telegram not configured", status_code=503)

    try:
        update_data = await request.json()
    except Exception:
        return Response(content="Invalid JSON", status_code=400)

    # Process in the request context (Telegram retries on timeout,
    # so we respond quickly and let the adapter handle it)
    try:
        await adapter.handle_update(update_data)
    except Exception as exc:
        logger.error("Telegram webhook error: %s", exc, exc_info=True)

    # Telegram expects 200 OK regardless
    return Response(status_code=200)


@telegram_router.get("/status")
async def telegram_status(request: Request) -> dict:
    """Return Telegram channel status."""
    adapter = getattr(request.app.state, "telegram_adapter", None)
    if adapter is None:
        return {"status": "not_configured"}

    return {
        "status": "active",
        "mode": adapter.mode,
        "bot_username": adapter.bot_username or "unknown",
    }
