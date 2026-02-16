"""Tests for the custom tool sandbox — discovery, registry, instantiation, CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from vandelay.tools.registry import ToolRegistry, _custom_tools_changed, _discover_custom_tools


# -- Fixtures ------------------------------------------------------------------

VALID_TOOLKIT_CODE = '''\
"""A test custom tool."""
from agno.tools import Toolkit

class GreeterTools(Toolkit):
    """Says hello."""

    def __init__(self):
        super().__init__(name="greeter")
        self.register(self.greet)

    def greet(self, name: str) -> str:
        """Greet someone."""
        return f"Hello, {name}!"
'''

NO_TOOLKIT_CODE = '''\
"""Just a plain module with no Toolkit subclass."""

class Helper:
    pass
'''

BROKEN_CODE = '''\
"""This module has a syntax error."""
def broken(
'''


@pytest.fixture
def custom_dir(tmp_path: Path) -> Path:
    d = tmp_path / "custom_tools"
    d.mkdir()
    return d


# -- Discovery tests ----------------------------------------------------------

class TestDiscoverCustomTools:
    def test_empty_dir(self, custom_dir: Path):
        result = _discover_custom_tools(custom_dir)
        assert result == {}

    def test_missing_dir(self, tmp_path: Path):
        result = _discover_custom_tools(tmp_path / "nonexistent")
        assert result == {}

    def test_valid_toolkit(self, custom_dir: Path):
        (custom_dir / "greeter.py").write_text(VALID_TOOLKIT_CODE)
        result = _discover_custom_tools(custom_dir)
        assert "greeter" in result
        assert result["greeter"]["class_name"] == "GreeterTools"
        assert result["greeter"]["category"] == "custom"
        assert result["greeter"]["module_path"] == "vandelay_custom_greeter"

    def test_no_toolkit_class(self, custom_dir: Path):
        (custom_dir / "helper.py").write_text(NO_TOOLKIT_CODE)
        result = _discover_custom_tools(custom_dir)
        assert result == {}

    def test_import_error(self, custom_dir: Path):
        (custom_dir / "broken.py").write_text(BROKEN_CODE)
        result = _discover_custom_tools(custom_dir)
        assert result == {}

    def test_skips_underscore_files(self, custom_dir: Path):
        (custom_dir / "_internal.py").write_text(VALID_TOOLKIT_CODE)
        result = _discover_custom_tools(custom_dir)
        assert result == {}

    def test_description_from_docstring(self, custom_dir: Path):
        (custom_dir / "greeter.py").write_text(VALID_TOOLKIT_CODE)
        result = _discover_custom_tools(custom_dir)
        assert result["greeter"]["description"] == "Says hello."


# -- Registry integration tests -----------------------------------------------

class TestCustomToolInRegistry:
    def test_custom_tool_appears_after_refresh(self, custom_dir: Path, tmp_path: Path):
        (custom_dir / "greeter.py").write_text(VALID_TOOLKIT_CODE)
        cache_path = tmp_path / "registry.json"
        registry = ToolRegistry(cache_path=cache_path)

        # Monkey-patch CUSTOM_TOOLS_DIR for this test
        import vandelay.tools.registry as reg_mod
        original = reg_mod.CUSTOM_TOOLS_DIR
        reg_mod.CUSTOM_TOOLS_DIR = custom_dir
        try:
            registry.refresh()
            entry = registry.get("greeter")
            assert entry is not None
            assert entry.class_name == "GreeterTools"
            assert entry.category == "custom"
            assert entry.pricing == "open_source"
            assert entry.is_builtin is True
        finally:
            reg_mod.CUSTOM_TOOLS_DIR = original


# -- Cache invalidation tests -------------------------------------------------

class TestCacheInvalidation:
    def test_no_change(self, custom_dir: Path, tmp_path: Path):
        cache_file = tmp_path / "registry.json"
        cache_file.write_text("{}")
        assert not _custom_tools_changed(custom_dir, cache_file.stat().st_mtime)

    def test_new_file_triggers(self, custom_dir: Path, tmp_path: Path):
        import time

        cache_file = tmp_path / "registry.json"
        cache_file.write_text("{}")
        cache_mtime = cache_file.stat().st_mtime

        time.sleep(0.05)  # ensure mtime difference
        (custom_dir / "new_tool.py").write_text(VALID_TOOLKIT_CODE)
        assert _custom_tools_changed(custom_dir, cache_mtime)

    def test_nonexistent_dir(self, tmp_path: Path):
        assert not _custom_tools_changed(tmp_path / "nope", 0.0)


# -- Manager instantiation tests ----------------------------------------------

class TestCustomToolInstantiation:
    def test_instantiate_custom_tool(self, custom_dir: Path, tmp_path: Path):
        (custom_dir / "greeter.py").write_text(VALID_TOOLKIT_CODE)
        cache_path = tmp_path / "registry.json"
        registry = ToolRegistry(cache_path=cache_path)

        import vandelay.tools.registry as reg_mod
        original = reg_mod.CUSTOM_TOOLS_DIR
        reg_mod.CUSTOM_TOOLS_DIR = custom_dir
        try:
            registry.refresh()

            from vandelay.tools.manager import ToolManager

            # Patch CUSTOM_TOOLS_DIR in manager module too
            from unittest.mock import patch
            with patch("vandelay.config.constants.CUSTOM_TOOLS_DIR", custom_dir):
                manager = ToolManager(registry=registry)
                instances = manager.instantiate_tools(["greeter"])
                assert len(instances) == 1
                result = instances[0].greet(name="World")
                assert result == "Hello, World!"
        finally:
            reg_mod.CUSTOM_TOOLS_DIR = original


# -- CLI create command tests --------------------------------------------------

class TestCreateCommand:
    def test_creates_template(self, tmp_path: Path):
        from unittest.mock import patch

        from typer.testing import CliRunner

        from vandelay.cli.tools_commands import app

        runner = CliRunner()
        with patch("vandelay.config.constants.CUSTOM_TOOLS_DIR", tmp_path):
            result = runner.invoke(app, ["create", "my_tool"])

        assert result.exit_code == 0
        assert "Created custom tool" in result.output

        created = tmp_path / "my_tool.py"
        assert created.exists()
        content = created.read_text()
        assert "class MyToolTools(Toolkit):" in content
        assert 'super().__init__(name="my_tool")' in content

    def test_rejects_invalid_name(self):
        from typer.testing import CliRunner

        from vandelay.cli.tools_commands import app

        runner = CliRunner()
        result = runner.invoke(app, ["create", "123bad"])
        assert result.exit_code == 1
        assert "Invalid name" in result.output

    def test_rejects_existing(self, tmp_path: Path):
        from unittest.mock import patch

        from typer.testing import CliRunner

        from vandelay.cli.tools_commands import app

        (tmp_path / "dupe.py").write_text("# existing")
        runner = CliRunner()
        with patch("vandelay.config.constants.CUSTOM_TOOLS_DIR", tmp_path):
            result = runner.invoke(app, ["create", "dupe"])
        assert result.exit_code == 1
        assert "already exists" in result.output
