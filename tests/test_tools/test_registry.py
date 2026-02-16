"""Tests for the tool registry — discovery, caching, search."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vandelay.tools.registry import ToolEntry, ToolRegistry


@pytest.fixture
def tmp_registry(tmp_path: Path) -> ToolRegistry:
    """Registry using a temp cache file."""
    return ToolRegistry(cache_path=tmp_path / "tool_registry.json")


def test_refresh_discovers_tools(tmp_registry: ToolRegistry):
    """refresh() should find tools in the agno package."""
    count = tmp_registry.refresh()
    assert count > 0
    assert "shell" in tmp_registry.tools
    assert "file" in tmp_registry.tools


def test_shell_tool_entry(tmp_registry: ToolRegistry):
    """Shell tool should be correctly categorised as built-in."""
    tmp_registry.refresh()
    shell = tmp_registry.get("shell")
    assert shell is not None
    assert shell.class_name == "ShellTools"
    assert shell.module_path == "agno.tools.shell"
    assert shell.is_builtin is True
    assert shell.category == "system"


def test_cache_persists(tmp_path: Path):
    """Registry should save to and load from disk cache."""
    cache_file = tmp_path / "tool_registry.json"
    reg1 = ToolRegistry(cache_path=cache_file)
    reg1.refresh()

    assert cache_file.exists()
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "tools" in data
    assert "refreshed_at" in data

    # Load from cache (no refresh needed)
    reg2 = ToolRegistry(cache_path=cache_file)
    assert len(reg2.tools) == len(reg1.tools)


def test_search_by_name(tmp_registry: ToolRegistry):
    """search() should find tools by name substring."""
    tmp_registry.refresh()
    results = tmp_registry.search("shell")
    names = [t.name for t in results]
    assert "shell" in names


def test_search_by_category(tmp_registry: ToolRegistry):
    """search() should find tools by category or name match."""
    tmp_registry.refresh()
    results = tmp_registry.search("system")
    assert len(results) > 0
    # "system" category should include shell
    names = [t.name for t in results]
    assert "shell" in names


def test_by_category(tmp_registry: ToolRegistry):
    """by_category() should group tools."""
    tmp_registry.refresh()
    cats = tmp_registry.by_category()
    assert "system" in cats
    assert any(t.name == "shell" for t in cats["system"])


def test_builtin_tools(tmp_registry: ToolRegistry):
    """builtin_tools() should only return tools with no deps."""
    tmp_registry.refresh()
    builtins = tmp_registry.builtin_tools()
    assert all(t.is_builtin for t in builtins)
    assert all(len(t.pip_dependencies) == 0 for t in builtins)


def test_tool_entry_serialization():
    """ToolEntry should round-trip through dict."""
    entry = ToolEntry(
        name="test_tool",
        module_path="agno.tools.test",
        class_name="TestTools",
        category="testing",
        pip_dependencies=["test-pkg"],
        is_builtin=False,
    )
    d = entry.to_dict()
    restored = ToolEntry.from_dict(d)
    assert restored.name == entry.name
    assert restored.pip_dependencies == entry.pip_dependencies
    assert restored.is_builtin is False


def test_internal_modules_excluded(tmp_registry: ToolRegistry):
    """Internal agno modules should not appear in the registry."""
    tmp_registry.refresh()
    assert "toolkit" not in tmp_registry.tools
    assert "function" not in tmp_registry.tools
    assert "models" not in tmp_registry.tools
    assert "decorator" not in tmp_registry.tools


def test_descriptions_extracted(tmp_registry: ToolRegistry):
    """Built-in tools should have extracted method descriptions."""
    tmp_registry.refresh()
    calculator = tmp_registry.get("calculator")
    assert calculator is not None
    assert calculator.description != ""
    assert "Methods:" in calculator.description


def test_description_excludes_base_methods(tmp_registry: ToolRegistry):
    """Descriptions should not include base Toolkit methods like 'register'."""
    tmp_registry.refresh()
    shell = tmp_registry.get("shell")
    assert shell is not None
    # Base methods should be filtered out
    assert "register —" not in shell.description
    assert "get_functions —" not in shell.description


def test_description_includes_tool_methods(tmp_registry: ToolRegistry):
    """Descriptions should include the actual tool methods."""
    tmp_registry.refresh()
    file_tool = tmp_registry.get("file")
    assert file_tool is not None
    assert "read_file" in file_tool.description
    assert "save_file" in file_tool.description


def test_pricing_on_builtin_tool(tmp_registry: ToolRegistry):
    """Built-in tools like shell should be open_source."""
    tmp_registry.refresh()
    shell = tmp_registry.get("shell")
    assert shell is not None
    assert shell.pricing == "open_source"


def test_pricing_on_free_tool(tmp_registry: ToolRegistry):
    """Tools with free API keys should be marked free."""
    tmp_registry.refresh()
    ddg = tmp_registry.get("duckduckgo")
    assert ddg is not None
    assert ddg.pricing == "free"


def test_pricing_on_paid_tool(tmp_registry: ToolRegistry):
    """Tools requiring paid API keys should be marked paid."""
    tmp_registry.refresh()
    tavily = tmp_registry.get("tavily")
    assert tavily is not None
    assert tavily.pricing == "paid"


def test_pricing_serialization():
    """Pricing should survive ToolEntry round-trip."""
    entry = ToolEntry(
        name="test_tool",
        module_path="agno.tools.test",
        class_name="TestTools",
        pricing="free",
    )
    d = entry.to_dict()
    restored = ToolEntry.from_dict(d)
    assert restored.pricing == "free"


def test_pricing_persists_in_cache(tmp_path: Path):
    """Pricing should survive cache round-trip."""
    cache_file = tmp_path / "tool_registry.json"
    reg1 = ToolRegistry(cache_path=cache_file)
    reg1.refresh()

    shell_pricing = reg1.get("shell").pricing

    reg2 = ToolRegistry(cache_path=cache_file)
    assert reg2.get("shell").pricing == shell_pricing


def test_description_persists_in_cache(tmp_path: Path):
    """Descriptions should survive cache round-trip."""
    cache_file = tmp_path / "tool_registry.json"
    reg1 = ToolRegistry(cache_path=cache_file)
    reg1.refresh()

    calc_desc = reg1.get("calculator").description

    reg2 = ToolRegistry(cache_path=cache_file)
    assert reg2.get("calculator").description == calc_desc
