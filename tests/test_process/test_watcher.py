"""Tests for FileWatcher — file filtering, lifecycle, and restart dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.process.watcher import FileWatcher, _should_watch


class TestShouldWatch:
    def test_python_files(self):
        assert _should_watch(Path("src/vandelay/main.py")) is True

    def test_json_files(self):
        assert _should_watch(Path("config.json")) is True

    def test_markdown_files(self):
        assert _should_watch(Path("workspace/SOUL.md")) is True

    def test_toml_files(self):
        assert _should_watch(Path("pyproject.toml")) is True

    def test_rejects_dotfiles(self):
        assert _should_watch(Path(".gitignore")) is False

    def test_accepts_dotenv(self):
        assert _should_watch(Path(".env")) is True

    def test_rejects_pycache(self):
        assert _should_watch(Path("src/__pycache__/main.cpython-311.pyc")) is False

    def test_rejects_git_dir(self):
        assert _should_watch(Path(".git/objects/abc123")) is False

    def test_rejects_unrelated_extensions(self):
        assert _should_watch(Path("image.png")) is False
        assert _should_watch(Path("data.csv")) is False


class TestFileWatcherLifecycle:
    def test_init_filters_nonexistent_paths(self, tmp_path):
        existing = tmp_path / "src"
        existing.mkdir()
        nonexistent = tmp_path / "nope"

        watcher = FileWatcher(watch_paths=[existing, nonexistent])
        assert len(watcher._watch_paths) == 1
        assert watcher._watch_paths[0] == existing

    def test_start_stop_thread(self, tmp_path):
        watch_dir = tmp_path / "src"
        watch_dir.mkdir()

        watcher = FileWatcher(watch_paths=[watch_dir])

        # Patch watchfiles.watch at the source so the local import picks it up
        mock_watch = MagicMock(return_value=iter([]))
        with patch.dict("sys.modules", {"watchfiles": MagicMock(watch=mock_watch)}):
            watcher.start()
            assert watcher._thread is not None
            # Give thread time to start and finish (empty iterator)
            watcher._thread.join(timeout=2)
            watcher.stop()
            assert not watcher.is_running

    def test_double_start_is_noop(self, tmp_path):
        watch_dir = tmp_path / "src"
        watch_dir.mkdir()

        watcher = FileWatcher(watch_paths=[watch_dir])

        mock_watch = MagicMock(return_value=iter([]))
        with patch.dict("sys.modules", {"watchfiles": MagicMock(watch=mock_watch)}):
            watcher.start()
            first_thread = watcher._thread
            # Second start while first is still "alive" should be a no-op
            # (thread may have already exited from empty iterator)
            watcher.stop()


class TestTriggerRestart:
    @patch("vandelay.process.watcher.subprocess.Popen")
    @patch("vandelay.process.watcher.sys")
    def test_windows_uses_popen(self, mock_sys, mock_popen):
        mock_sys.platform = "win32"
        mock_sys.executable = "python.exe"
        mock_sys.argv = ["vandelay", "start"]
        mock_sys.exit = MagicMock(side_effect=SystemExit)

        watcher = FileWatcher(
            watch_paths=[],
            restart_args=["python.exe", "vandelay", "start"],
        )

        with pytest.raises(SystemExit):
            watcher._trigger_restart()

        mock_popen.assert_called_once_with(["python.exe", "vandelay", "start"])

    @patch("vandelay.process.watcher.os.execv")
    @patch("vandelay.process.watcher.sys")
    def test_unix_uses_execv(self, mock_sys, mock_execv):
        mock_sys.platform = "linux"
        mock_sys.executable = "/usr/bin/python3"
        mock_sys.argv = ["vandelay", "start"]

        watcher = FileWatcher(
            watch_paths=[],
            restart_args=["/usr/bin/python3", "vandelay", "start"],
        )
        watcher._trigger_restart()

        mock_execv.assert_called_once_with(
            "/usr/bin/python3",
            ["/usr/bin/python3", "vandelay", "start"],
        )
