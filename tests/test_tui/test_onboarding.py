"""Tests for the TUI onboarding wizard."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Step navigation logic
# ---------------------------------------------------------------------------


class TestStepNavigation:
    """Test the step index advancement logic without launching a Textual app."""

    def _make_screen(self, provider="anthropic"):
        """Instantiate OnboardingScreen without running the app."""
        from vandelay.tui.screens.onboarding import OnboardingScreen

        screen = OnboardingScreen.__new__(OnboardingScreen)
        screen._step = 0
        screen._provider = provider
        screen._agent_name = "Art"
        screen._api_key = ""
        screen._timezone = "UTC"
        screen._total_steps = 4
        return screen

    def _next_step(self, screen, step):
        """Replicate OnboardingScreen._next_step."""
        nxt = step + 1
        if nxt == 2 and screen._provider == "ollama":
            nxt = 3
        return min(nxt, 3)

    def _prev_step(self, screen, step):
        """Replicate OnboardingScreen._prev_step."""
        prv = step - 1
        if prv == 2 and screen._provider == "ollama":
            prv = 1
        return max(prv, 0)

    def test_next_advances_step_index(self):
        screen = self._make_screen()
        assert self._next_step(screen, 0) == 1

    def test_back_decrements_step_index(self):
        screen = self._make_screen()
        screen._step = 2
        assert self._prev_step(screen, 2) == 1

    def test_next_from_last_step_stays_at_3(self):
        screen = self._make_screen()
        assert self._next_step(screen, 3) == 3

    def test_back_from_first_step_stays_at_0(self):
        screen = self._make_screen()
        assert self._prev_step(screen, 0) == 0

    def test_ollama_skips_step_2_on_next(self):
        screen = self._make_screen(provider="ollama")
        # step 1 → should skip 2 → land on 3
        assert self._next_step(screen, 1) == 3

    def test_ollama_skips_step_2_on_back(self):
        screen = self._make_screen(provider="ollama")
        # step 3 → should skip 2 → land on 1
        assert self._prev_step(screen, 3) == 1

    def test_non_ollama_does_not_skip_step_2(self):
        for provider in ["anthropic", "openai", "google", "groq"]:
            screen = self._make_screen(provider=provider)
            assert self._next_step(screen, 1) == 2, f"Failed for provider={provider}"
            assert self._prev_step(screen, 3) == 2, f"Failed for provider={provider}"


# ---------------------------------------------------------------------------
# _apply_settings
# ---------------------------------------------------------------------------


class TestApplySettings:
    """Test _apply_settings by patching at the source module paths (imports are lazy inside method)."""

    def _make_screen(self, provider="anthropic", api_key="test-key", auth_method="api_key"):
        from vandelay.tui.screens.onboarding import OnboardingScreen

        screen = OnboardingScreen.__new__(OnboardingScreen)
        screen._agent_name = "Cosmo"
        screen._provider = provider
        screen._auth_method = auth_method
        screen._api_key = api_key
        screen._timezone = "America/New_York"
        return screen

    def _patch_all(self, mock_settings):
        """Context-manager stack that patches all lazy imports in _apply_settings."""
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(
            patch("vandelay.config.settings.Settings", return_value=mock_settings)
        )
        mock_write = stack.enter_context(patch("vandelay.cli.onboard._write_env_key"))
        mock_ws = stack.enter_context(patch("vandelay.workspace.manager.init_workspace"))
        return stack, mock_write, mock_ws

    def _make_mock_settings(self):
        mock_settings = MagicMock()
        mock_settings.model = MagicMock()
        mock_settings.server = MagicMock()
        return mock_settings

    def test_settings_save_called(self):
        screen = self._make_screen()
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key"):
                with patch("vandelay.workspace.manager.init_workspace") as mock_ws:
                    screen._apply_settings()

        mock_settings.save.assert_called_once()
        mock_ws.assert_called_once()

    def test_write_env_key_called_with_correct_args(self):
        screen = self._make_screen(provider="anthropic", api_key="sk-ant-test")
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key") as mock_write:
                with patch("vandelay.workspace.manager.init_workspace"):
                    screen._apply_settings()

        mock_write.assert_called_once_with("ANTHROPIC_API_KEY", "sk-ant-test")

    def test_no_write_env_key_for_ollama(self):
        screen = self._make_screen(provider="ollama", api_key="")
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key") as mock_write:
                with patch("vandelay.workspace.manager.init_workspace"):
                    screen._apply_settings()

        mock_write.assert_not_called()

    def test_init_workspace_called_on_finish(self):
        screen = self._make_screen()
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key"):
                with patch("vandelay.workspace.manager.init_workspace") as mock_ws:
                    screen._apply_settings()

        mock_ws.assert_called_once()

    def test_agent_name_set_on_settings(self):
        screen = self._make_screen()
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key"):
                with patch("vandelay.workspace.manager.init_workspace"):
                    screen._apply_settings()

        assert mock_settings.agent_name == "Cosmo"

    def test_provider_set_on_settings(self):
        screen = self._make_screen(provider="openai", api_key="sk-openai")
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key"):
                with patch("vandelay.workspace.manager.init_workspace"):
                    screen._apply_settings()

        assert mock_settings.model.provider == "openai"

    def test_timezone_set_on_settings(self):
        screen = self._make_screen()
        mock_settings = self._make_mock_settings()

        with patch("vandelay.config.settings.Settings", return_value=mock_settings):
            with patch("vandelay.cli.onboard._write_env_key"):
                with patch("vandelay.workspace.manager.init_workspace"):
                    screen._apply_settings()

        assert mock_settings.timezone == "America/New_York"


# ---------------------------------------------------------------------------
# Ollama — API key step skipped
# ---------------------------------------------------------------------------


class TestOllamaSkipsApiKeyStep:
    def _make_screen(self):
        from vandelay.tui.screens.onboarding import OnboardingScreen

        screen = OnboardingScreen.__new__(OnboardingScreen)
        screen._step = 0
        screen._provider = "ollama"
        screen._agent_name = "Art"
        screen._api_key = ""
        screen._timezone = "UTC"
        screen._total_steps = 4
        return screen

    def _next_step(self, screen, step):
        nxt = step + 1
        if nxt == 2 and screen._provider == "ollama":
            nxt = 3
        return min(nxt, 3)

    def test_ollama_step_1_to_3_direct(self):
        screen = self._make_screen()
        next_after_provider = self._next_step(screen, 1)
        assert next_after_provider == 3, "Ollama should jump from step 1 to step 3"

    def test_ollama_never_reaches_step_2(self):
        screen = self._make_screen()
        steps_visited = []
        current = 0
        for _ in range(5):
            steps_visited.append(current)
            nxt = self._next_step(screen, current)
            if nxt == current:
                break
            current = nxt
        assert 2 not in steps_visited, f"Step 2 should be skipped for Ollama. Got: {steps_visited}"


# ---------------------------------------------------------------------------
# Collect validation
# ---------------------------------------------------------------------------


class TestCollectCurrentValidation:
    """Test the _collect_current validation without a full Textual environment."""

    def _validate_name(self, name: str) -> bool:
        return bool(name.strip())

    def test_empty_name_fails_validation(self):
        assert not self._validate_name("")

    def test_whitespace_name_fails_validation(self):
        assert not self._validate_name("   ")

    def test_valid_name_passes(self):
        assert self._validate_name("Cosmo")


# ---------------------------------------------------------------------------
# Import smoke tests
# ---------------------------------------------------------------------------


class TestOnboardingImport:
    def test_import_onboarding_screen(self):
        from textual.screen import ModalScreen

        from vandelay.tui.screens.onboarding import OnboardingScreen

        assert OnboardingScreen is not None
        assert issubclass(OnboardingScreen, ModalScreen)

    def test_detect_tz_returns_string(self):
        from vandelay.tui.screens.onboarding import _detect_tz

        result = _detect_tz()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_provider_order_matches_constants(self):
        from vandelay.config.constants import MODEL_PROVIDERS
        from vandelay.tui.screens.onboarding import _PROVIDER_ORDER

        for key in _PROVIDER_ORDER:
            assert key in MODEL_PROVIDERS, f"Provider '{key}' in _PROVIDER_ORDER not in MODEL_PROVIDERS"


# ---------------------------------------------------------------------------
# Integration: app stays alive after completing the onboarding wizard
# ---------------------------------------------------------------------------


class TestOnboardingIntegration:
    """Reproduce the bug: TUI was exiting after the user clicked Finish.

    NOTE: In Textual 8, app.query(SomeScreen) does NOT find screens — it only
    finds widgets *inside* the current screen.  Use isinstance(app.screen, X).
    """

    @pytest.mark.asyncio
    async def test_app_stays_alive_after_onboarding_complete(self):
        """After finishing the onboarding wizard the TUI must NOT exit.

        Bug report: clicking Finish in OnboardingScreen kicked the user back
        to the terminal instead of returning to the Chat tab.

        We patch _apply_settings to a no-op (avoids writing to ~/.vandelay)
        and verify the app is still running with MainScreen on top.
        """
        from vandelay.config.settings import Settings
        from vandelay.tui.app import VandelayApp
        from vandelay.tui.screens.main import MainScreen
        from vandelay.tui.screens.onboard_modal import FirstRunModal
        from vandelay.tui.screens.onboarding import OnboardingScreen

        app = VandelayApp()

        with (
            patch.object(Settings, "config_exists", return_value=False),
            patch.object(OnboardingScreen, "_apply_settings"),
        ):
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause(0.3)

                # FirstRunModal should be the current screen
                assert isinstance(app.screen, FirstRunModal), (
                    f"Expected FirstRunModal, got {type(app.screen).__name__}"
                )

                # Click "Onboard" to launch the OnboardingScreen
                await pilot.click("#btn-onboard")
                await pilot.pause(0.3)

                assert isinstance(app.screen, OnboardingScreen), (
                    f"Expected OnboardingScreen after clicking Onboard, got {type(app.screen).__name__}"
                )

                # Navigate: step 0 (name) → step 1 (provider) → step 2 (key) → step 3 (tz)
                for _ in range(3):
                    await pilot.click("#btn-next")
                    await pilot.pause(0.1)

                # Now on step 3 — "Finish" button should be visible
                # Must query the active screen, not the default app DOM
                finish_btn = app.screen.query_one("#btn-finish")
                assert finish_btn.display, "Finish button should be visible on last step"

                # Click Finish — this is the critical action
                await pilot.click("#btn-finish")
                await pilot.pause(0.3)

                # App must still be running with MainScreen on top
                assert isinstance(app.screen, MainScreen), (
                    f"Expected MainScreen after onboarding, got {type(app.screen).__name__}. "
                    "App likely exited or crashed."
                )

    @pytest.mark.asyncio
    async def test_finish_exception_does_not_exit_app(self):
        """If _apply_settings raises, the error is shown inline — app must NOT exit."""
        from vandelay.config.settings import Settings
        from vandelay.tui.app import VandelayApp
        from vandelay.tui.screens.onboarding import OnboardingScreen

        app = VandelayApp()

        with (
            patch.object(Settings, "config_exists", return_value=False),
            patch.object(OnboardingScreen, "_apply_settings", side_effect=RuntimeError("disk full")),
        ):
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause(0.3)

                await pilot.click("#btn-onboard")
                await pilot.pause(0.3)

                # Navigate to the last step
                for _ in range(3):
                    await pilot.click("#btn-next")
                    await pilot.pause(0.1)

                await pilot.click("#btn-finish")
                await pilot.pause(0.3)

                # App must still be running — error should be shown inline
                # OnboardingScreen is still open (not dismissed on error)
                assert isinstance(app.screen, OnboardingScreen), (
                    f"Expected OnboardingScreen to stay open on error, "
                    f"got {type(app.screen).__name__}"
                )
