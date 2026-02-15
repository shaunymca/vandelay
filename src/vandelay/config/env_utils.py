"""Utilities for reading and writing the ~/.vandelay/.env file."""

from __future__ import annotations

from pathlib import Path

from vandelay.config.constants import VANDELAY_HOME


def write_env_key(env_key: str, value: str, env_path: Path | None = None) -> None:
    """Write or update a key in the .env file.

    Parameters
    ----------
    env_key:
        The environment variable name (e.g. ``TELEGRAM_TOKEN``).
    value:
        The value to store.
    env_path:
        Override .env location (default: ``~/.vandelay/.env``).
    """
    if env_path is None:
        env_path = VANDELAY_HOME / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing lines
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    # Update existing key or append
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}="):
            lines[i] = f"{env_key}={value}"
            found = True
            break

    if not found:
        lines.append(f"{env_key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_env_file(env_path: Path | None = None) -> dict[str, str]:
    """Parse the .env file and return key-value pairs.

    Strips inline comments (``# ...``) and whitespace.
    """
    if env_path is None:
        env_path = VANDELAY_HOME / ".env"

    result: dict[str, str] = {}
    if not env_path.exists():
        return result

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if " #" in v:
                v = v[: v.index(" #")]
            result[k] = v.strip()
    except OSError:
        pass

    return result
