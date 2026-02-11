"""Tests for daemon CLI — systemd, launchd, and Windows dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vandelay.cli.daemon import (
    _find_vandelay_executable,
    _launchd_plist_content,
    _systemd_unit_content,
    install_daemon_service,
    is_daemon_supported,
)


class TestFindExecutable:
    def test_finds_via_shutil_which(self):
        with patch("vandelay.cli.daemon.shutil.which", return_value="/usr/bin/vandelay"):
            result = _find_vandelay_executable()
            assert result == "/usr/bin/vandelay"

    def test_fallback_to_python_module(self):
        with patch("vandelay.cli.daemon.shutil.which", return_value=None):
            result = _find_vandelay_executable()
            assert "-m vandelay.cli.main" in result


class TestSystemdUnit:
    def test_unit_contains_exec_start(self):
        content = _systemd_unit_content("/usr/bin/vandelay")
        assert "ExecStart=/usr/bin/vandelay start --server" in content

    def test_unit_has_required_sections(self):
        content = _systemd_unit_content("/usr/bin/vandelay")
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content

    def test_unit_restart_on_failure(self):
        content = _systemd_unit_content("/usr/bin/vandelay")
        assert "Restart=on-failure" in content

    def test_unit_logs_to_vandelay_log(self):
        content = _systemd_unit_content("/usr/bin/vandelay")
        assert "vandelay.log" in content


class TestLaunchdPlist:
    def test_plist_contains_label(self):
        content = _launchd_plist_content("/usr/bin/vandelay")
        assert "com.vandelay.agent" in content

    def test_plist_contains_program_arguments(self):
        content = _launchd_plist_content("/usr/bin/vandelay")
        assert "<string>/usr/bin/vandelay</string>" in content
        assert "<string>start</string>" in content
        assert "<string>--server</string>" in content

    def test_plist_keep_alive(self):
        content = _launchd_plist_content("/usr/bin/vandelay")
        assert "<key>KeepAlive</key>" in content

    def test_plist_logs_to_vandelay_log(self):
        content = _launchd_plist_content("/usr/bin/vandelay")
        assert "vandelay.log" in content


class TestDaemonCommands:
    """Test command dispatch by platform."""

    @patch("vandelay.cli.daemon._platform", return_value="windows")
    def test_install_windows_unsupported(self, mock_plat):
        from typer.testing import CliRunner

        from vandelay.cli.daemon import app

        runner = CliRunner()
        result = runner.invoke(app, ["install"])
        assert result.exit_code != 0
        assert "not supported on Windows" in result.output

    @patch("vandelay.cli.daemon._platform", return_value="linux")
    @patch("vandelay.cli.daemon._systemd_install")
    @patch("vandelay.cli.daemon._find_vandelay_executable", return_value="/usr/bin/vandelay")
    def test_install_linux_calls_systemd(self, mock_exe, mock_install, mock_plat):
        from typer.testing import CliRunner

        from vandelay.cli.daemon import app

        runner = CliRunner()
        result = runner.invoke(app, ["install"])
        mock_install.assert_called_once_with("/usr/bin/vandelay")

    @patch("vandelay.cli.daemon._platform", return_value="darwin")
    @patch("vandelay.cli.daemon._launchd_install")
    @patch("vandelay.cli.daemon._find_vandelay_executable", return_value="/usr/bin/vandelay")
    def test_install_darwin_calls_launchd(self, mock_exe, mock_install, mock_plat):
        from typer.testing import CliRunner

        from vandelay.cli.daemon import app

        runner = CliRunner()
        result = runner.invoke(app, ["install"])
        mock_install.assert_called_once_with("/usr/bin/vandelay")

    @patch("vandelay.cli.daemon._platform", return_value="windows")
    def test_status_windows_unsupported(self, mock_plat):
        from typer.testing import CliRunner

        from vandelay.cli.daemon import app

        runner = CliRunner()
        result = runner.invoke(app, ["status"])
        assert result.exit_code != 0
        assert "not supported on Windows" in result.output


class TestPublicAPI:
    """Tests for the public helper functions used by onboarding."""

    @patch("vandelay.cli.daemon._platform", return_value="linux")
    def test_is_daemon_supported_linux(self, mock_plat):
        assert is_daemon_supported() is True

    @patch("vandelay.cli.daemon._platform", return_value="darwin")
    def test_is_daemon_supported_macos(self, mock_plat):
        assert is_daemon_supported() is True

    @patch("vandelay.cli.daemon._platform", return_value="windows")
    def test_is_daemon_supported_windows(self, mock_plat):
        assert is_daemon_supported() is False

    @patch("vandelay.cli.daemon._platform", return_value="windows")
    def test_install_daemon_service_unsupported(self, mock_plat):
        assert install_daemon_service() is False

    @patch("vandelay.cli.daemon._platform", return_value="linux")
    @patch("vandelay.cli.daemon._systemd_install")
    @patch("vandelay.cli.daemon._find_vandelay_executable", return_value="/usr/bin/vandelay")
    def test_install_daemon_service_linux(self, mock_exe, mock_install, mock_plat):
        assert install_daemon_service() is True
        mock_install.assert_called_once_with("/usr/bin/vandelay")

    @patch("vandelay.cli.daemon._platform", return_value="darwin")
    @patch("vandelay.cli.daemon._launchd_install")
    @patch("vandelay.cli.daemon._find_vandelay_executable", return_value="/usr/bin/vandelay")
    def test_install_daemon_service_macos(self, mock_exe, mock_install, mock_plat):
        assert install_daemon_service() is True
        mock_install.assert_called_once_with("/usr/bin/vandelay")

    @patch("vandelay.cli.daemon._platform", return_value="linux")
    @patch("vandelay.cli.daemon._systemd_install", side_effect=RuntimeError("boom"))
    @patch("vandelay.cli.daemon._find_vandelay_executable", return_value="/usr/bin/vandelay")
    def test_install_daemon_service_failure(self, mock_exe, mock_install, mock_plat):
        assert install_daemon_service() is False
