"""Tests for health and status endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vandelay.server.routes.health import health_router


def _make_test_app(test_settings):
    """Create a minimal FastAPI app with health routes for testing."""
    app = FastAPI()
    app.state.settings = test_settings
    app.state.started_at = datetime.now(timezone.utc)
    app.include_router(health_router)
    return app


def test_health_returns_ok(test_settings):
    """GET /health should return status ok."""
    app = _make_test_app(test_settings)
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert data["agent_name"] == "TestClaw"
    assert "version" in data
    assert data["uptime_seconds"] >= 0


def test_status_returns_config(test_settings):
    """GET /status should return config summary."""
    app = _make_test_app(test_settings)
    client = TestClient(app)

    resp = client.get("/status")
    assert resp.status_code == 200

    data = resp.json()
    assert data["agent_name"] == "TestClaw"
    assert data["model_provider"] == "ollama"
    assert data["model_id"] == "llama3.1"
    assert data["safety_mode"] == "confirm"
    assert data["channels"] == []
    assert data["server_port"] == 8000
    assert "started_at" in data
    assert "version" in data
