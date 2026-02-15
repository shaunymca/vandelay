"""Tests for the tool manager — enable/disable, instantiation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from vandelay.config.models import ModelConfig, SafetyConfig
from vandelay.config.settings import Settings
from vandelay.tools.manager import ToolManager
from vandelay.tools.registry import ToolRegistry


@pytest.fixture
def tmp_manager(tmp_path: Path) -> ToolManager:
    """Manager with a fresh registry cache."""
    registry = ToolRegistry(cache_path=tmp_path / "tool_registry.json")
    registry.refresh()
    return ToolManager(registry=registry)


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        agent_name="TestClaw",
        model=ModelConfig(provider="ollama", model_id="llama3.1"),
        safety=SafetyConfig(mode="tiered"),
        workspace_dir=str(tmp_path / "workspace"),
        enabled_tools=["shell", "file"],
        db_url="",
    )


def test_list_tools_returns_data(tmp_manager: ToolManager):
    """list_tools should return a list of dicts with expected keys."""
    tools = tmp_manager.list_tools()
    assert len(tools) > 0
    first = tools[0]
    assert "name" in first
    assert "category" in first
    assert "enabled" in first
    assert "installed" in first


def test_list_tools_shows_enabled(tmp_manager: ToolManager):
    """Enabled tools should be marked as enabled."""
    tools = tmp_manager.list_tools(enabled_tools=["shell"])
    shell = next(t for t in tools if t["name"] == "shell")
    assert shell["enabled"] is True

    file_tool = next(t for t in tools if t["name"] == "file")
    assert file_tool["enabled"] is False


def test_list_tools_filter_category(tmp_manager: ToolManager):
    """Category filter should work."""
    tools = tmp_manager.list_tools(category="system")
    assert all(t["category"] == "system" for t in tools)


def test_instantiate_builtin_tools(tmp_manager: ToolManager, test_settings: Settings):
    """Should instantiate built-in tools without errors."""
    instances = tmp_manager.instantiate_tools(["file"], settings=test_settings)
    assert len(instances) == 1
    assert instances[0].__class__.__name__ == "FileTools"


def test_instantiate_shell_returns_safe_shell(tmp_manager: ToolManager, test_settings: Settings):
    """Shell tool should be wrapped in SafeShellTools."""
    instances = tmp_manager.instantiate_tools(["shell"], settings=test_settings)
    assert len(instances) == 1
    assert instances[0].__class__.__name__ == "SafeShellTools"


def test_instantiate_unknown_tool_skipped(tmp_manager: ToolManager, test_settings: Settings):
    """Unknown tool names should be silently skipped."""
    instances = tmp_manager.instantiate_tools(["nonexistent_tool_xyz"], settings=test_settings)
    assert len(instances) == 0


def test_categories(tmp_manager: ToolManager):
    """categories() should return sorted unique category names."""
    cats = tmp_manager.categories()
    assert "system" in cats
    assert cats == sorted(cats)


def test_refresh(tmp_manager: ToolManager):
    """refresh() should re-scan and return count."""
    count = tmp_manager.refresh()
    assert count > 0


# --- Google Sheets output truncation ---

class _FakeSheetTool:
    """Minimal stand-in for GoogleSheetsTools with a read_sheet method."""
    def read_sheet(self, *args, **kwargs):
        return self._response


def test_sheet_output_truncated_when_large():
    """read_sheet output exceeding 50K chars should be truncated with guidance."""
    from vandelay.tools.manager import _cap_sheet_output

    fake = _FakeSheetTool()
    fake._response = "x" * 100_000
    _cap_sheet_output(fake)

    result = fake.read_sheet()
    assert len(result) < 100_000
    assert result.startswith("x" * 50_000)
    assert "[TRUNCATED" in result
    assert "100,000 chars" in result
    assert "spreadsheet_range" in result


def test_sheet_output_unchanged_when_small():
    """read_sheet output under the limit should pass through untouched."""
    from vandelay.tools.manager import _cap_sheet_output

    fake = _FakeSheetTool()
    fake._response = "small data"
    _cap_sheet_output(fake)

    result = fake.read_sheet()
    assert result == "small data"


# --- FileTools source code write protection ---

class _FakeFileTools:
    """Minimal stand-in for Agno FileTools."""
    def save_file(self, contents="", file_name="", **kw):
        return f"saved {file_name}"

    def replace_file_chunk(self, file_name="", start_line=0, end_line=0, chunk="", **kw):
        return f"replaced in {file_name}"

    def delete_file(self, file_name=""):
        return f"deleted {file_name}"


def test_file_write_blocked_for_source_code():
    """FileTools should block writes to src/vandelay paths."""
    from vandelay.tools.manager import _guard_file_writes

    fake = _FakeFileTools()
    _guard_file_writes(fake)

    result = fake.save_file(contents="hack", file_name="/home/vandelay/vandelay/src/vandelay/tools/manager.py")
    assert "BLOCKED" in result
    assert "source code" in result


def test_file_delete_blocked_for_source_code():
    """FileTools should block deletes of src/vandelay paths."""
    from vandelay.tools.manager import _guard_file_writes

    fake = _FakeFileTools()
    _guard_file_writes(fake)

    result = fake.delete_file(file_name="/home/vandelay/vandelay/src/vandelay/core/chat_service.py")
    assert "BLOCKED" in result


def test_file_replace_blocked_for_source_code():
    """FileTools should block replace_file_chunk on src/vandelay paths."""
    from vandelay.tools.manager import _guard_file_writes

    fake = _FakeFileTools()
    _guard_file_writes(fake)

    result = fake.replace_file_chunk(file_name="src/vandelay/config/models.py", start_line=1, end_line=5, chunk="bad")
    assert "BLOCKED" in result


def test_file_write_allowed_for_non_source():
    """FileTools should allow writes to paths outside src/vandelay."""
    from vandelay.tools.manager import _guard_file_writes

    fake = _FakeFileTools()
    _guard_file_writes(fake)

    result = fake.save_file(contents="ok", file_name="/home/vandelay/work/script.py")
    assert result == "saved /home/vandelay/work/script.py"

    result = fake.delete_file(file_name="/home/vandelay/work/old.txt")
    assert result == "deleted /home/vandelay/work/old.txt"
