"""Tests for CamoufoxTools toolkit."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vandelay.tools.camoufox import CamoufoxTools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tools():
    return CamoufoxTools(headless=True)


def _make_mock_page(url: str = "https://example.com", title: str = "Example"):
    """Create a mock Playwright sync page."""
    page = MagicMock()
    page.url = url
    page.title.return_value = title
    page.inner_text.return_value = "Page text content"
    page.eval_on_selector_all.return_value = [
        {"text": "Example", "href": "https://example.com"},
        {"text": "Docs", "href": "https://docs.example.com"},
    ]
    page.accessibility = MagicMock()
    page.accessibility.snapshot.return_value = None
    return page


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

def test_instantiation():
    tools = CamoufoxTools()
    assert tools.name == "camoufox"
    assert tools._headless is True
    assert tools._browser is None
    assert tools._pages == {}


def test_instantiation_headless_false():
    tools = CamoufoxTools(headless=False)
    assert tools._headless is False


# ---------------------------------------------------------------------------
# Key regression: sync functions must be in self.functions, not async_functions
#
# Root cause of prod bug: all methods were async, so Agno registered them in
# self.async_functions only. In sync delegation paths the LLM tool schema is
# built from self.functions — so the model saw no CamouFox functions at all.
# ---------------------------------------------------------------------------

def test_functions_registered_as_sync():
    """All CamoufoxTools methods must be in self.functions (sync dict)."""
    tools = CamoufoxTools()
    expected = {
        "open_tab", "navigate", "get_page_content", "click",
        "type_text", "screenshot", "scroll", "get_links",
        "close_tab", "list_tabs",
    }
    assert expected == set(tools.functions.keys()), (
        "CamoufoxTools functions should all be sync so they appear in "
        "self.functions regardless of whether the agent runs sync or async"
    )


def test_no_async_functions():
    """CamoufoxTools should have no entries in async_functions."""
    tools = CamoufoxTools()
    assert tools.async_functions == {}, (
        "Async functions would be invisible to sync agent delegation paths"
    )


# ---------------------------------------------------------------------------
# Tool methods — mocked sync Playwright
# ---------------------------------------------------------------------------

def test_open_tab(tools):
    mock_page = _make_mock_page()
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    tools._context = mock_context

    result = tools.open_tab("https://example.com")
    assert "tab1" in result
    assert "Example" in result
    mock_page.goto.assert_called_once()


def test_navigate(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.navigate("tab1", "https://other.com")
    assert "tab1" in result
    mock_page.goto.assert_called_once()


def test_navigate_missing_tab(tools):
    result = tools.navigate("tab99", "https://other.com")
    assert "not found" in result


def test_get_page_content_fallback(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.get_page_content("tab1")
    assert "Page text content" in result


def test_get_page_content_a11y(tools):
    mock_page = _make_mock_page()
    mock_page.accessibility.snapshot.return_value = {
        "role": "WebArea",
        "name": "Example",
        "children": [{"role": "heading", "name": "Hello"}],
    }
    tools._pages["tab1"] = mock_page

    result = tools.get_page_content("tab1")
    assert "heading" in result
    assert "Hello" in result


def test_click(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.click("tab1", "button.submit")
    assert "Clicked" in result
    mock_page.click.assert_called_once_with("button.submit", timeout=10000)


def test_type_text(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.type_text("tab1", "input#email", "test@example.com")
    assert "Typed" in result
    mock_page.fill.assert_called_once_with("input#email", "test@example.com", timeout=10000)


def test_screenshot(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.screenshot("tab1")
    assert "Screenshot saved" in result
    mock_page.screenshot.assert_called_once()


def test_screenshot_custom_path(tools, tmp_path):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page
    save_path = str(tmp_path / "shots" / "page.png")

    result = tools.screenshot("tab1", path=save_path)
    assert "Screenshot saved" in result
    mock_page.screenshot.assert_called_once_with(path=save_path, full_page=False)


def test_scroll(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.scroll("tab1", "down")
    assert "Scrolled down" in result
    mock_page.evaluate.assert_called_once()


def test_get_links(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.get_links("tab1")
    assert "Example" in result
    assert "https://docs.example.com" in result


def test_close_tab(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.close_tab("tab1")
    assert "tab1" in result
    assert "closed" in result.lower()
    assert "tab1" not in tools._pages


def test_list_tabs(tools):
    tools._pages["tab1"] = _make_mock_page(url="https://example.com")
    tools._pages["tab2"] = _make_mock_page(url="https://docs.example.com")

    result = tools.list_tabs()
    assert "tab1" in result
    assert "tab2" in result


def test_list_tabs_empty(tools):
    result = tools.list_tabs()
    assert "No open tabs" in result


# ---------------------------------------------------------------------------
# Browser lifecycle
# ---------------------------------------------------------------------------

def test_close_shuts_down(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page
    tools._browser = MagicMock()
    tools._context = MagicMock()

    tools.close()
    assert tools._pages == {}
    assert tools._browser is None
    assert tools._context is None


def test_lazy_start():
    """_ensure_browser should start the sync browser on first call."""
    tools = CamoufoxTools()

    mock_ctx = MagicMock()
    mock_browser = MagicMock()
    mock_browser.__enter__ = MagicMock(return_value=mock_ctx)
    mock_browser.__exit__ = MagicMock(return_value=False)

    mock_module = MagicMock()
    mock_module.Camoufox = MagicMock(return_value=mock_browser)

    with patch.dict(sys.modules, {"camoufox.sync_api": mock_module}):
        tools._ensure_browser()

    assert tools._context is mock_ctx


# ---------------------------------------------------------------------------
# Registry inclusion
# ---------------------------------------------------------------------------

def test_registry_includes_camoufox(tmp_path: Path):
    """Camoufox should appear in the tool registry after refresh."""
    from vandelay.tools.registry import ToolRegistry

    registry = ToolRegistry(cache_path=tmp_path / "tool_registry.json")
    registry.refresh()

    entry = registry.get("camoufox")
    assert entry is not None
    assert entry.class_name == "CamoufoxTools"
    assert entry.category == "browser"
    assert entry.module_path == "vandelay.tools.camoufox"
    assert entry.pip_dependencies == ["camoufox[geoip]"]
