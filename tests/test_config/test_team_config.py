"""Tests for TeamConfig and MemberConfig models."""

from vandelay.config.models import MemberConfig, TeamConfig


class TestMemberConfig:
    def test_defaults(self):
        mc = MemberConfig(name="test")
        assert mc.name == "test"
        assert mc.role == ""
        assert mc.tools == []
        assert mc.model_provider == ""
        assert mc.model_id == ""
        assert mc.instructions == []
        assert mc.instructions_file == ""

    def test_full_config(self):
        mc = MemberConfig(
            name="cto",
            role="Technical Co-Founder",
            tools=["shell", "file"],
            model_provider="anthropic",
            model_id="claude-sonnet-4-5-20250929",
            instructions=["Be helpful"],
            instructions_file="cto.md",
        )
        assert mc.name == "cto"
        assert mc.role == "Technical Co-Founder"
        assert mc.tools == ["shell", "file"]
        assert mc.model_provider == "anthropic"
        assert mc.model_id == "claude-sonnet-4-5-20250929"
        assert mc.instructions == ["Be helpful"]
        assert mc.instructions_file == "cto.md"

    def test_serialization_roundtrip(self):
        mc = MemberConfig(
            name="research",
            tools=["tavily"],
            model_provider="openai",
            model_id="gpt-4o",
        )
        data = mc.model_dump()
        restored = MemberConfig(**data)
        assert restored.name == "research"
        assert restored.tools == ["tavily"]
        assert restored.model_provider == "openai"


class TestTeamConfig:
    def test_defaults(self):
        cfg = TeamConfig()
        assert cfg.enabled is False
        assert cfg.mode == "route"
        assert cfg.members == ["browser", "system", "scheduler", "knowledge"]

    def test_enabled(self):
        cfg = TeamConfig(enabled=True)
        assert cfg.enabled is True

    def test_default_mode_is_route(self):
        cfg = TeamConfig()
        assert cfg.mode == "route"

    def test_custom_mode(self):
        cfg = TeamConfig(mode="coordinate")
        assert cfg.mode == "coordinate"

    def test_custom_members_strings(self):
        cfg = TeamConfig(members=["browser", "system"])
        assert cfg.members == ["browser", "system"]

    def test_mixed_members(self):
        """String and MemberConfig members can coexist."""
        mc = MemberConfig(name="cto", tools=["shell"])
        cfg = TeamConfig(members=["browser", mc])
        assert len(cfg.members) == 2
        assert cfg.members[0] == "browser"
        assert isinstance(cfg.members[1], MemberConfig)
        assert cfg.members[1].name == "cto"

    def test_serialization_roundtrip_strings(self):
        cfg = TeamConfig(enabled=True, mode="coordinate", members=["system", "knowledge"])
        data = cfg.model_dump()
        restored = TeamConfig(**data)
        assert restored.enabled is True
        assert restored.mode == "coordinate"
        assert restored.members == ["system", "knowledge"]

    def test_serialization_roundtrip_rich_members(self):
        mc = MemberConfig(
            name="cto",
            tools=["shell", "file"],
            model_provider="anthropic",
            model_id="claude-sonnet-4-5-20250929",
        )
        cfg = TeamConfig(enabled=True, mode="route", members=["browser", mc])
        data = cfg.model_dump()
        restored = TeamConfig(**data)
        assert restored.enabled is True
        assert restored.mode == "route"
        assert len(restored.members) == 2
        assert restored.members[0] == "browser"
        # Rich member deserializes back as MemberConfig
        rich = restored.members[1]
        assert isinstance(rich, MemberConfig)
        assert rich.name == "cto"
        assert rich.model_provider == "anthropic"
