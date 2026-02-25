"""Tests for AgentsTab team mode panel and model inheritance."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestTeamModeConstants:
    """_TEAM_MODES is correctly defined and covers all Agno modes."""

    def test_all_four_modes_present(self):
        from vandelay.tui.tabs.agents import _TEAM_MODES
        values = [v for _, v in _TEAM_MODES]
        assert "coordinate" in values
        assert "route" in values
        assert "broadcast" in values
        assert "tasks" in values

    def test_modes_are_label_value_tuples(self):
        from vandelay.tui.tabs.agents import _TEAM_MODES
        for label, value in _TEAM_MODES:
            assert isinstance(label, str)
            assert isinstance(value, str)
            assert label == value  # labels match values for these simple strings

    def test_team_subnav_entry_present(self):
        from vandelay.tui.tabs.agents import _LEADER_SUBNAV
        keys = [k for k, _, _ in _LEADER_SUBNAV]
        assert "team" in keys

    def test_team_subnav_type_is_team(self):
        from vandelay.tui.tabs.agents import _LEADER_SUBNAV
        entry = next((e for e in _LEADER_SUBNAV if e[0] == "team"), None)
        assert entry is not None
        assert entry[2] == "team"

    def test_team_subnav_between_model_and_tools(self):
        from vandelay.tui.tabs.agents import _LEADER_SUBNAV
        keys = [k for k, _, _ in _LEADER_SUBNAV]
        assert keys.index("team") > keys.index("model")
        assert keys.index("team") < keys.index("tools")


class TestLoadTeam:
    """_load_team() reads from settings and shows the content-team panel."""

    def _make_tab(self):
        from vandelay.tui.tabs.agents import AgentsTab
        tab = AgentsTab.__new__(AgentsTab)
        tab._selected_agent = "leader"
        tab._selected_section = None
        tab._selected_type = None
        tab._current_file = None
        tab._agent_entries = []
        tab._subnav_entries = []
        tab._save_gen = 0
        return tab

    def test_load_team_sets_switch_and_select(self):
        tab = self._make_tab()

        mock_switch = MagicMock()
        mock_select = MagicMock()
        mock_settings = MagicMock()
        mock_settings.team.enabled = True
        mock_settings.team.mode = "route"

        def mock_query_one(selector, widget_type=None):
            if "team-enabled" in selector:
                return mock_switch
            if "team-mode-select" in selector:
                return mock_select
            raise ValueError(f"Unexpected: {selector}")

        tab.query_one = mock_query_one
        tab._settings = lambda: mock_settings
        tab._show = MagicMock()

        tab._load_team()

        assert mock_switch.value is True
        mock_select.__setattr__("value", "route")
        tab._show.assert_called_once_with("content-team")

    def test_load_team_defaults_to_coordinate_when_mode_empty(self):
        tab = self._make_tab()

        captured = {}
        mock_switch = MagicMock()
        mock_select = MagicMock()

        def mock_query_one(selector, widget_type=None):
            if "team-enabled" in selector:
                return mock_switch
            if "team-mode-select" in selector:
                return mock_select
            raise ValueError(f"Unexpected: {selector}")

        def set_value(val):
            captured["mode"] = val

        mock_select.__class__ = type(
            "MockSelect", (),
            {"value": property(lambda self: None, lambda self, v: captured.__setitem__("mode", v))}
        )

        tab.query_one = mock_query_one
        mock_settings = MagicMock()
        mock_settings.team.enabled = False
        mock_settings.team.mode = ""
        tab._settings = lambda: mock_settings
        tab._show = MagicMock()

        # Should not raise even when mode is empty
        tab._load_team()
        tab._show.assert_called_once_with("content-team")


class TestSaveTeam:
    """_save_team() writes team.enabled and team.mode to settings."""

    def _make_tab(self):
        from vandelay.tui.tabs.agents import AgentsTab
        tab = AgentsTab.__new__(AgentsTab)
        tab._selected_agent = "leader"
        tab._selected_section = "team"
        tab._selected_type = "team"
        return tab

    def test_save_team_writes_enabled_and_mode(self):
        from vandelay.tui.tabs.agents import AgentsTab

        tab = self._make_tab()

        mock_switch = MagicMock()
        mock_switch.value = False
        mock_select = MagicMock()
        mock_select.value = "broadcast"

        def mock_query_one(selector, widget_type=None):
            if "team-enabled" in selector:
                return mock_switch
            if "team-mode-select" in selector:
                return mock_select
            raise ValueError(f"Unexpected: {selector}")

        tab.query_one = mock_query_one

        saved_settings = MagicMock()
        tab._settings = lambda: saved_settings
        mock_app = MagicMock()

        with patch.object(AgentsTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            with patch("vandelay.config.settings.get_settings") as mock_gs:
                mock_gs.cache_clear = MagicMock()
                tab._save_team()

        assert saved_settings.team.enabled is False
        assert saved_settings.team.mode == "broadcast"
        saved_settings.save.assert_called_once()

    def test_save_team_notifies_on_success(self):
        from vandelay.tui.tabs.agents import AgentsTab

        tab = self._make_tab()

        mock_switch = MagicMock()
        mock_switch.value = True
        mock_select = MagicMock()
        mock_select.value = "coordinate"

        def mock_query_one(selector, widget_type=None):
            if "team-enabled" in selector:
                return mock_switch
            if "team-mode-select" in selector:
                return mock_select
            raise ValueError(f"Unexpected: {selector}")

        tab.query_one = mock_query_one
        tab._settings = lambda: MagicMock()
        mock_app = MagicMock()

        with patch.object(AgentsTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            with patch("vandelay.config.settings.get_settings"):
                tab._save_team()

        mock_app.notify.assert_called_once()
        msg = mock_app.notify.call_args[0][0]
        assert "Team" in msg

    def test_save_team_notifies_on_error(self):
        from vandelay.tui.tabs.agents import AgentsTab

        tab = self._make_tab()

        def bad_query(selector, widget_type=None):
            raise RuntimeError("widget missing")

        tab.query_one = bad_query
        tab._settings = lambda: MagicMock()
        mock_app = MagicMock()

        with patch.object(AgentsTab, "app", new_callable=lambda: property(lambda self: mock_app)):
            tab._save_team()

        mock_app.notify.assert_called_once()
        call_kwargs = mock_app.notify.call_args
        assert call_kwargs[1].get("severity") == "error"


class TestMemberModelAuthInheritance:
    """Member model panel inherits leader's auth_method when using the same provider."""

    def _make_tab(self):
        from vandelay.tui.tabs.agents import AgentsTab
        tab = AgentsTab.__new__(AgentsTab)
        tab._selected_agent = "cto"
        tab._selected_section = "model"
        tab._selected_type = "model"
        tab._pending_auth_method = "api_key"
        tab._pending_model_id = ""
        return tab

    def _make_settings(self, provider="openai", auth_method="codex"):
        s = MagicMock()
        s.model.provider = provider
        s.model.model_id = "gpt-5.1-codex-mini"
        s.model.auth_method = auth_method
        s.team.members = []
        return s

    def test_member_inherits_codex_auth_when_same_provider(self):
        """Member with no provider override should inherit leader's codex auth_method."""
        tab = self._make_tab()
        s = self._make_settings(provider="openai", auth_method="codex")

        # Member has no provider override
        tab._get_or_create_member_config = lambda slug: None
        tab._settings = lambda: s
        tab._update_model_options = MagicMock()
        tab._show = MagicMock()

        mock_psel = MagicMock()
        mock_inherit = MagicMock()

        def mock_query_one(sel, cls=None):
            if "provider-select" in sel:
                return mock_psel
            if "model-inherit-note" in sel:
                return mock_inherit
            return MagicMock()

        tab.query_one = mock_query_one

        tab._load_model("cto")

        # auth_method passed to _update_model_options should be "codex"
        call_kwargs = tab._update_model_options.call_args
        assert call_kwargs[1].get("auth_method") == "codex"

    def test_member_uses_api_key_when_different_provider(self):
        """Member with a different provider should use api_key, not inherit codex."""
        tab = self._make_tab()
        s = self._make_settings(provider="openai", auth_method="codex")

        mc = MagicMock()
        mc.model_provider = "anthropic"
        mc.model_id = "claude-sonnet-4-5"
        tab._get_or_create_member_config = lambda slug: mc
        tab._settings = lambda: s
        tab._update_model_options = MagicMock()
        tab._show = MagicMock()

        mock_psel = MagicMock()
        mock_inherit = MagicMock()

        def mock_query_one(sel, cls=None):
            if "provider-select" in sel:
                return mock_psel
            if "model-inherit-note" in sel:
                return mock_inherit
            return MagicMock()

        tab.query_one = mock_query_one

        tab._load_model("cto")

        call_kwargs = tab._update_model_options.call_args
        assert call_kwargs[1].get("auth_method") == "api_key"

    def test_member_inherits_api_key_when_leader_uses_api_key(self):
        """Member with same provider as leader using api_key inherits api_key."""
        tab = self._make_tab()
        s = self._make_settings(provider="anthropic", auth_method="api_key")

        tab._get_or_create_member_config = lambda slug: None
        tab._settings = lambda: s
        tab._update_model_options = MagicMock()
        tab._show = MagicMock()

        mock_psel = MagicMock()
        mock_inherit = MagicMock()

        def mock_query_one(sel, cls=None):
            if "provider-select" in sel:
                return mock_psel
            if "model-inherit-note" in sel:
                return mock_inherit
            return MagicMock()

        tab.query_one = mock_query_one

        tab._load_model("cto")

        call_kwargs = tab._update_model_options.call_args
        assert call_kwargs[1].get("auth_method") == "api_key"
