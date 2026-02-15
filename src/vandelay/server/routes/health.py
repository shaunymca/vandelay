"""Health and status endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vandelay import __version__

health_router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    agent_name: str
    version: str
    uptime_seconds: float


class StatusResponse(BaseModel):
    agent_name: str
    model_provider: str
    model_id: str
    safety_mode: str
    timezone: str
    channels: list[str]
    server_host: str
    server_port: int
    started_at: str
    version: str
    traces_endpoint: str = "/traces"
    total_traces: int = 0


@health_router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    started_at = getattr(request.app.state, "started_at", datetime.now(UTC))
    uptime = (datetime.now(UTC) - started_at).total_seconds()
    return HealthResponse(
        status="ok",
        agent_name=settings.agent_name,
        version=__version__,
        uptime_seconds=round(uptime, 1),
    )


@health_router.get("/status", response_model=StatusResponse)
async def status(request: Request) -> StatusResponse:
    settings = request.app.state.settings
    started_at = getattr(request.app.state, "started_at", datetime.now(UTC))

    # Show actually registered channels (not just enabled in config)
    channel_router = getattr(request.app.state, "channel_router", None)
    channels: list[str] = channel_router.active_channels if channel_router else []

    # Get trace count if tracing is enabled
    total_traces = 0
    db = getattr(request.app.state, "db", None)
    if db is not None:
        try:
            _, count = db.get_traces(limit=1)
            total_traces = count or 0
        except Exception:
            pass

    return StatusResponse(
        agent_name=settings.agent_name,
        model_provider=settings.model.provider,
        model_id=settings.model.model_id,
        safety_mode=settings.safety.mode,
        timezone=settings.timezone,
        channels=channels,
        server_host=settings.server.host,
        server_port=settings.server.port,
        started_at=started_at.isoformat(),
        version=__version__,
        total_traces=total_traces,
    )
