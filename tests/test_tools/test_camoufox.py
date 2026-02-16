"""Tests for CamoufoxTools toolkit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vandelay.tools.camoufox import CamoufoxTools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tools():
    return CamoufoxTools(headless=True)


def _make_mock_page(url: str = "https://example.com", title: str = "Example"):
    """Create a mock Playwright page with standard async methods."""
    page = AsyncMock()
    page.url = url
    page.title.return_value = title
    page.inner_text.return_value = "Page text content"
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.close = AsyncMock()
    page.evaluate = AsyncMock()
    page.screenshot = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.eval_on_selector_all = AsyncMock(return_value=[
        {"text": "Example", "href": "https://example.com"},
        {"text": "Docs", "href": "https://docs.example.com"},
    ])
    page.accessibility = MagicMock()
    page.accessibility.snapshot = AsyncMock(return_value=None)
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
# Tool methods — mocked Playwright
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_open_tab(tools):
    mock_page = _make_mock_page()
    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    # Bypass _ensure_browser
    tools._context = mock_context

    result = await tools.open_tab("https://example.com")
    assert "tab1" in result
    assert "Example" in result
    mock_page.goto.assert_awaited_once()


@pytest.mark.asyncio
async def test_navigate(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.navigate("tab1", "https://other.com")
    assert "tab1" in result
    mock_page.goto.assert_awaited_once()


@pytest.mark.asyncio
async def test_navigate_missing_tab(tools):
    result = await tools.navigate("tab99", "https://other.com")
    assert "not found" in result


@pytest.mark.asyncio
async def test_get_page_content_fallback(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.get_page_content("tab1")
    assert "Page text content" in result


@pytest.mark.asyncio
async def test_get_page_content_a11y(tools):
    mock_page = _make_mock_page()
    mock_page.accessibility.snapshot.return_value = {
        "role": "WebArea",
        "name": "Example",
        "children": [{"role": "heading", "name": "Hello"}],
    }
    tools._pages["tab1"] = mock_page

    result = await tools.get_page_content("tab1")
    assert "heading" in result
    assert "Hello" in result


@pytest.mark.asyncio
async def test_click(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.click("tab1", "button.submit")
    assert "Clicked" in result
    mock_page.click.assert_awaited_once_with("button.submit", timeout=10000)


@pytest.mark.asyncio
async def test_type_text(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.type_text("tab1", "input#email", "test@example.com")
    assert "Typed" in result
    mock_page.fill.assert_awaited_once_with("input#email", "test@example.com", timeout=10000)


@pytest.mark.asyncio
async def test_screenshot(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.screenshot("tab1")
    assert "Screenshot saved" in result
    mock_page.screenshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_scroll(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.scroll("tab1", "down")
    assert "Scrolled down" in result
    mock_page.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_links(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.get_links("tab1")
    assert "Example" in result
    assert "https://docs.example.com" in result


@pytest.mark.asyncio
async def test_close_tab(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = await tools.close_tab("tab1")
    assert "tab1" in result
    assert "closed" in result.lower()
    assert "tab1" not in tools._pages


@pytest.mark.asyncio
async def test_list_tabs(tools):
    tools._pages["tab1"] = _make_mock_page(url="https://example.com")
    tools._pages["tab2"] = _make_mock_page(url="https://docs.example.com")

    result = await tools.list_tabs()
    assert "tab1" in result
    assert "tab2" in result


@pytest.mark.asyncio
async def test_list_tabs_empty(tools):
    result = await tools.list_tabs()
    assert "No open tabs" in result


# ---------------------------------------------------------------------------
# Browser lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_close_shuts_down(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page
    tools._browser = AsyncMock()
    tools._context = AsyncMock()

    await tools.close()
    assert tools._pages == {}
    assert tools._browser is None
    assert tools._context is None


@pytest.mark.asyncio
async def test_lazy_start():
    """_ensure_browser should start the browser on first call."""
    import sys

    tools = CamoufoxTools()

    mock_ctx = AsyncMock()
    mock_browser = MagicMock()
    mock_browser.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_browser.__aexit__ = AsyncMock()

    mock_module = MagicMock()
    mock_module.AsyncCamoufox = MagicMock(return_value=mock_browser)

    with patch.dict(sys.modules, {"camoufox.async_api": mock_module}):
        await tools._ensure_browser()

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
