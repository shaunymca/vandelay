"""Shared fixtures for integration tests.

These tests hit real APIs with real credentials. They are excluded from
default pytest runs via the ``-m 'not integration'`` addopts in
pyproject.toml.  Run them explicitly with::

    uv run pytest tests/integration/ -m integration -v

Credentials are loaded from files **inside this directory** (gitignored):

    tests/integration/.env              — NOTION_API_KEY, etc.
    tests/integration/google_token.json — unified Google OAuth token

See the .example files for the expected format.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from vandelay.config.env_utils import read_env_file
from vandelay.tools.manager import _inject_google_creds

INTEGRATION_DIR = Path(__file__).parent
LOCAL_ENV = INTEGRATION_DIR / ".env"
LOCAL_GOOGLE_TOKEN = INTEGRATION_DIR / "google_token.json"


@pytest.fixture(scope="session", autouse=True)
def _load_test_env() -> None:
    """Inject tests/integration/.env vars into the process environment."""
    env_vars = read_env_file(LOCAL_ENV)
    for key, value in env_vars.items():
        os.environ.setdefault(key, value)


# ---------------------------------------------------------------------------
# Google fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def google_token_path() -> Path:
    if not LOCAL_GOOGLE_TOKEN.exists():
        pytest.skip(
            f"Google token not found at {LOCAL_GOOGLE_TOKEN} — "
            "copy from ~/.vandelay/google_token.json or see google_token.json.example"
        )
    return LOCAL_GOOGLE_TOKEN


def _make_google_tool(tool_cls, token_path: Path):
    """Instantiate a Google tool class and inject unified credentials."""
    tool = tool_cls()
    _inject_google_creds(tool, str(token_path))
    if not getattr(tool, "creds", None) or not tool.creds.valid:
        pytest.skip(f"Google credentials invalid for {tool_cls.__name__}")
    return tool


@pytest.fixture(scope="session")
def sheets_tool(google_token_path: Path):
    from agno.tools.googlesheets import GoogleSheetsTools

    return _make_google_tool(GoogleSheetsTools, google_token_path)


@pytest.fixture(scope="session")
def calendar_tool(google_token_path: Path):
    from agno.tools.googlecalendar import GoogleCalendarTools

    tool = GoogleCalendarTools(allow_update=True)
    _inject_google_creds(tool, str(google_token_path))
    if not getattr(tool, "creds", None) or not tool.creds.valid:
        pytest.skip("Google credentials invalid for GoogleCalendarTools")
    return tool


@pytest.fixture(scope="session")
def gmail_tool(google_token_path: Path):
    from agno.tools.gmail import GmailTools

    return _make_google_tool(GmailTools, google_token_path)


@pytest.fixture(scope="session")
def drive_tool(google_token_path: Path, _load_test_env):
    from agno.tools.google_drive import GoogleDriveTools

    quota_project = os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT_ID")
    if not quota_project:
        pytest.skip("GOOGLE_CLOUD_QUOTA_PROJECT_ID not set")
    tool = GoogleDriveTools(quota_project_id=quota_project)
    _inject_google_creds(tool, str(google_token_path))
    if not getattr(tool, "creds", None) or not tool.creds.valid:
        pytest.skip("Google credentials invalid for GoogleDriveTools")
    return tool


# ---------------------------------------------------------------------------
# Notion fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def notion_tool(_load_test_env):
    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        pytest.skip("NOTION_API_KEY and/or NOTION_DATABASE_ID not set")

    from agno.tools.notion import NotionTools

    return NotionTools()
