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
    t = CamoufoxTools(headless=True)
    yield t
    t._executor.shutdown(wait=False)


def _make_mock_page(url: str = "https://example.com", title: str = "Example"):
    """Create a mock Playwright sync page."""
    page = MagicMock()
    page.url = url
    page.title.return_value = title
    page.inner_text.return_value = "Page text content"
    page.content.return_value = "<html><body>Page HTML</body></html>"
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

def test_instantiation_defaults():
    t = CamoufoxTools()
    assert t.name == "camoufox"
    assert t._launch_config["headless"] is True
    assert t._launch_config["disable_coop"] is True
    assert t._launch_config["humanize"] is True
    assert t._launch_config["geoip"] is True
    assert t._browser is None
    assert t._pages == {}
    t._executor.shutdown(wait=False)


def test_instantiation_headless_false():
    t = CamoufoxTools(headless=False)
    assert t._launch_config["headless"] is False
    t._executor.shutdown(wait=False)


def test_instantiation_with_proxy():
    t = CamoufoxTools(proxy={"server": "http://proxy:8080"})
    assert t._launch_config["proxy"]["server"] == "http://proxy:8080"
    t._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Key regression: sync functions must be in self.functions, not async_functions
#
# Root cause of prod bug: all methods were async, so Agno registered them in
# self.async_functions only. In sync delegation paths the LLM tool schema is
# built from self.functions — so the model saw no CamouFox functions at all.
# ---------------------------------------------------------------------------

EXPECTED_FUNCTIONS = {
    "configure_browser", "restart_browser", "get_browser_config",
    "open_tab", "navigate", "close_tab", "list_tabs", "get_url",
    "get_page_content", "get_html", "get_links",
    "click", "type_text", "scroll", "execute_js",
    "wait_for_element", "wait_for_url",
    "screenshot",
}


def test_functions_registered_as_sync():
    """All CamoufoxTools methods must be in self.functions (sync dict)."""
    t = CamoufoxTools()
    assert EXPECTED_FUNCTIONS == set(t.functions.keys()), (
        "CamoufoxTools functions should all be sync so they appear in "
        "self.functions regardless of whether the agent runs sync or async"
    )
    t._executor.shutdown(wait=False)


def test_no_async_functions():
    """CamoufoxTools should have no entries in async_functions."""
    t = CamoufoxTools()
    assert t.async_functions == {}, (
        "Async functions would be invisible to sync agent delegation paths"
    )
    t._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Parameter schema extraction — Agno must be able to build tool schemas
# ---------------------------------------------------------------------------

def test_open_tab_parameter_schema():
    t = CamoufoxTools()
    func = t.functions["open_tab"].model_copy(deep=True)
    func.process_entrypoint(strict=False)
    schema = func.to_dict()
    props = schema["parameters"]["properties"]
    assert "url" in props
    assert props["url"]["type"] == "string"
    assert "url" in schema["parameters"]["required"]
    t._executor.shutdown(wait=False)


def test_configure_browser_parameter_schema():
    t = CamoufoxTools()
    func = t.functions["configure_browser"].model_copy(deep=True)
    func.process_entrypoint(strict=False)
    schema = func.to_dict()
    props = schema["parameters"]["properties"]
    assert "disable_coop" in props
    assert "humanize" in props
    assert "proxy_server" in props
    assert "locale" in props
    t._executor.shutdown(wait=False)


def test_wait_for_element_parameter_schema():
    t = CamoufoxTools()
    func = t.functions["wait_for_element"].model_copy(deep=True)
    func.process_entrypoint(strict=False)
    schema = func.to_dict()
    props = schema["parameters"]["properties"]
    assert "tab_id" in props
    assert "selector" in props
    assert "timeout" in props
    t._executor.shutdown(wait=False)


def test_all_functions_have_schemas():
    """Every registered function must produce a valid parameter schema."""
    t = CamoufoxTools()
    no_params = {"list_tabs", "get_browser_config", "restart_browser"}
    for name, func in t.functions.items():
        f = func.model_copy(deep=True)
        f.process_entrypoint(strict=False)
        schema = f.to_dict()
        assert "parameters" in schema, f"{name} missing parameters key"
        if name not in no_params:
            props = schema["parameters"].get("properties", {})
            assert props, f"{name} has no parameter schema — check type annotations"
    t._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Browser lifecycle
# ---------------------------------------------------------------------------

def test_configure_browser_updates_config(tools):
    result = tools.configure_browser(disable_coop=False, locale="fr-FR")
    assert tools._launch_config["disable_coop"] is False
    assert tools._launch_config["locale"] == "fr-FR"
    assert "Browser config updated" in result


def test_configure_browser_with_proxy(tools):
    result = tools.configure_browser(proxy_server="http://proxy:8080", proxy_username="u", proxy_password="p")
    assert tools._launch_config["proxy"]["server"] == "http://proxy:8080"
    assert tools._launch_config["proxy"]["username"] == "u"
    assert "Browser config updated" in result


def test_get_browser_config_no_browser(tools):
    result = tools.get_browser_config()
    assert "not started" in result
    assert "disable_coop" in result


def test_get_browser_config_redacts_proxy(tools):
    tools._launch_config["proxy"] = {"server": "http://proxy:8080", "username": "u", "password": "secret"}
    result = tools.get_browser_config()
    assert "secret" not in result
    assert "***" in result


def test_lazy_start_with_disable_coop():
    """_ensure_browser should pass disable_coop and i_know_what_im_doing to Camoufox."""
    t = CamoufoxTools(disable_coop=True)

    mock_ctx = MagicMock()
    mock_browser = MagicMock()
    mock_browser.__enter__ = MagicMock(return_value=mock_ctx)
    mock_browser.__exit__ = MagicMock(return_value=False)
    MockCamoufox = MagicMock(return_value=mock_browser)

    mock_module = MagicMock()
    mock_module.Camoufox = MockCamoufox

    with patch.dict(sys.modules, {"camoufox.sync_api": mock_module}):
        t._ensure_browser()

    call_kwargs = MockCamoufox.call_args[1]
    assert call_kwargs.get("disable_coop") is True
    assert call_kwargs.get("i_know_what_im_doing") is True
    t._executor.shutdown(wait=False)


def test_lazy_start_no_disable_coop():
    """When disable_coop=False, i_know_what_im_doing should not be set."""
    t = CamoufoxTools(disable_coop=False)

    mock_ctx = MagicMock()
    mock_browser = MagicMock()
    mock_browser.__enter__ = MagicMock(return_value=mock_ctx)
    mock_browser.__exit__ = MagicMock(return_value=False)
    MockCamoufox = MagicMock(return_value=mock_browser)

    mock_module = MagicMock()
    mock_module.Camoufox = MockCamoufox

    with patch.dict(sys.modules, {"camoufox.sync_api": mock_module}):
        t._ensure_browser()

    call_kwargs = MockCamoufox.call_args[1]
    assert "i_know_what_im_doing" not in call_kwargs
    t._executor.shutdown(wait=False)


def test_close_shuts_down(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page
    tools._browser = MagicMock()
    tools._context = MagicMock()

    tools.close()
    assert tools._pages == {}
    assert tools._browser is None
    assert tools._context is None


# ---------------------------------------------------------------------------
# Tab management
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


def test_close_tab(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.close_tab("tab1")
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


def test_get_url(tools):
    mock_page = _make_mock_page(url="https://example.com")
    tools._pages["tab1"] = mock_page

    result = tools.get_url("tab1")
    assert "https://example.com" in result


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

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


def test_get_html(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.get_html("tab1")
    assert "<html>" in result


def test_get_links(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.get_links("tab1")
    assert "Example" in result
    assert "https://docs.example.com" in result


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------

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


def test_scroll(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.scroll("tab1", "down")
    assert "Scrolled down" in result
    mock_page.evaluate.assert_called_once()


def test_execute_js(tools):
    mock_page = _make_mock_page()
    mock_page.evaluate.return_value = "Example Domain"
    tools._pages["tab1"] = mock_page

    result = tools.execute_js("tab1", "document.title")
    assert "Example Domain" in result
    mock_page.evaluate.assert_called_once_with("document.title")


def test_execute_js_none_result(tools):
    mock_page = _make_mock_page()
    mock_page.evaluate.return_value = None
    tools._pages["tab1"] = mock_page

    result = tools.execute_js("tab1", "console.log('x')")
    assert "no return value" in result


# ---------------------------------------------------------------------------
# Waiting
# ---------------------------------------------------------------------------

def test_wait_for_element_success(tools):
    mock_page = _make_mock_page()
    tools._pages["tab1"] = mock_page

    result = tools.wait_for_element("tab1", "#dashboard", timeout=5)
    assert "appeared" in result
    mock_page.wait_for_selector.assert_called_once_with("#dashboard", timeout=5000)


def test_wait_for_element_timeout(tools):
    mock_page = _make_mock_page()
    mock_page.wait_for_selector.side_effect = Exception("Timeout")
    tools._pages["tab1"] = mock_page

    result = tools.wait_for_element("tab1", "#missing", timeout=1)
    assert "Timed out" in result


def test_wait_for_url_success(tools):
    mock_page = _make_mock_page(url="https://app.commonroom.io/home")
    tools._pages["tab1"] = mock_page

    result = tools.wait_for_url("tab1", "commonroom.io/home", timeout=10)
    assert "matched" in result


def test_wait_for_url_timeout(tools):
    mock_page = _make_mock_page()
    mock_page.wait_for_url.side_effect = Exception("Timeout")
    tools._pages["tab1"] = mock_page

    result = tools.wait_for_url("tab1", "dashboard", timeout=1)
    assert "Timed out" in result


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Registry
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
