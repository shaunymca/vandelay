"""Workspace initialization and template management."""

from __future__ import annotations

import shutil
from pathlib import Path

from vandelay.config.constants import KNOWLEDGE_DIR, MEMBERS_DIR, WORKSPACE_DIR

# Templates are shipped inside the package
_TEMPLATES_DIR = Path(__file__).parent / "templates"

TEMPLATE_FILES = [
    "SOUL.md",
    "USER.md",
    "AGENTS.md",
    "BOOTSTRAP.md",
    "HEARTBEAT.md",
    "TOOLS.md",
]


def init_workspace(workspace_dir: Path | None = None) -> Path:
    """Create the workspace directory and copy default templates if missing.

    Returns the resolved workspace path.
    """
    ws = workspace_dir or WORKSPACE_DIR
    ws.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    MEMBERS_DIR.mkdir(parents=True, exist_ok=True)

    # Create memory subdirectory for daily logs
    (ws / "memory").mkdir(parents=True, exist_ok=True)

    for name in TEMPLATE_FILES:
        dest = ws / name
        if not dest.exists():
            src = _TEMPLATES_DIR / name
            if src.exists():
                shutil.copy2(src, dest)

    return ws


def get_template_content(name: str, workspace_dir: Path | None = None) -> str:
    """Read a workspace template file. Falls back to the shipped default."""
    ws = workspace_dir or WORKSPACE_DIR
    user_file = ws / name
    if user_file.exists():
        return user_file.read_text(encoding="utf-8")

    default_file = _TEMPLATES_DIR / name
    if default_file.exists():
        return default_file.read_text(encoding="utf-8")

    return ""


def workspace_is_initialized(workspace_dir: Path | None = None) -> bool:
    ws = workspace_dir or WORKSPACE_DIR
    return ws.exists() and (ws / "SOUL.md").exists()
