"""File watcher — monitors source/config/workspace for changes, triggers restart."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

logger = logging.getLogger("vandelay.process.watcher")

# Extensions worth watching
_WATCHED_EXTENSIONS = {".py", ".json", ".md", ".toml"}

# Directories/files to skip
_SKIP_NAMES = {"__pycache__", ".git", ".ruff_cache", ".mypy_cache", "node_modules"}


def _should_watch(path: Path) -> bool:
    """Return True if this file change should trigger a restart."""
    name = path.name

    # Skip dotfiles (except .env which is a config file)
    if name.startswith(".") and name != ".env":
        return False

    # Skip known junk directories
    for part in path.parts:
        if part in _SKIP_NAMES:
            return False

    # .env is special — name-based match (suffix == ".env" but not in the set)
    if name == ".env":
        return True

    return path.suffix in _WATCHED_EXTENSIONS


class FileWatcher:
    """Watches directories for changes and triggers a process restart.

    Uses ``watchfiles`` for efficient cross-platform FS watching with a
    debounce period to avoid restart storms.
    """

    def __init__(
        self,
        watch_paths: list[Path],
        restart_args: list[str] | None = None,
        debounce_ms: int = 1000,
    ) -> None:
        self._watch_paths = [p for p in watch_paths if p.exists()]
        self._restart_args = restart_args or [sys.executable] + sys.argv
        self._debounce_ms = debounce_ms
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the file watcher in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="vandelay-file-watcher",
        )
        self._thread.start()
        logger.info(
            "File watcher started — monitoring %s",
            ", ".join(str(p) for p in self._watch_paths),
        )

    def stop(self) -> None:
        """Signal the watcher to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        logger.info("File watcher stopped.")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _watch_loop(self) -> None:
        """Block on watchfiles.watch() and trigger restart on changes."""
        try:
            from watchfiles import watch

            for changes in watch(
                *self._watch_paths,
                stop_event=self._stop_event,
                debounce=self._debounce_ms,
                step=200,
            ):
                # Filter to only relevant file types
                relevant = [
                    (change_type, path)
                    for change_type, path in changes
                    if _should_watch(Path(path))
                ]

                if not relevant:
                    continue

                changed_files = [Path(p).name for _, p in relevant[:5]]
                logger.info(
                    "File changes detected (%d files): %s — restarting...",
                    len(relevant),
                    ", ".join(changed_files),
                )
                self._trigger_restart()
                break  # After triggering restart we don't continue

        except ImportError:
            logger.error(
                "watchfiles not installed — auto-restart disabled. "
                "Install with: uv add watchfiles"
            )
        except Exception:
            if not self._stop_event.is_set():
                logger.exception("File watcher error")

    def _trigger_restart(self) -> None:
        """Replace the current process with a fresh one."""
        args = self._restart_args

        if sys.platform == "win32":
            # Windows doesn't support os.execv reliably — spawn + exit
            logger.info("Spawning new process (Windows): %s", " ".join(args))
            subprocess.Popen(args)
            sys.exit(0)
        else:
            # Unix: exec replaces current process
            logger.info("Exec-replacing process: %s", " ".join(args))
            os.execv(args[0], args)
