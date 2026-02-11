"""Tests for CamofoxTools toolkit and CamofoxServer lifecycle."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vandelay.tools.camofox import CamofoxTools
from vandelay.tools.camofox_server import CamofoxServer


# ---------------------------------------------------------------------------
# CamofoxTools — mocked httpx tests
# ---------------------------------------------------------------------------

class FakeResponse:
    """Minimal mock for httpx.Response."""

    def __init__(self, data: dict, status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "error", request=MagicMock(), response=self
            )


class FakeAsyncClient:
    """Async context manager that returns mocked HTTP methods."""

    def __init__(self, response: FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, **kwargs):
        return self._response

    async def get(self, url, **kwargs):
        return self._response

    async def delete(self, url, **kwargs):
        return self._response


@pytest.fixture
def tools():
    return CamofoxTools(base_url="http://test:9377")


@pytest.mark.asyncio
async def test_create_tab(tools):
    resp = FakeResponse({"id": "tab1", "snapshot": "Page content here"})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.create_tab("https://example.com")
    assert "tab1" in result
    assert "Page content here" in result


@pytest.mark.asyncio
async def test_snapshot(tools):
    resp = FakeResponse({"snapshot": "<snapshot data>"})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.snapshot("tab1")
    assert "<snapshot data>" in result


@pytest.mark.asyncio
async def test_click(tools):
    resp = FakeResponse({"snapshot": "after click"})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.click("tab1", "e1")
    assert "after click" in result


@pytest.mark.asyncio
async def test_type_text(tools):
    resp = FakeResponse({"snapshot": "after type"})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.type_text("tab1", "e2", "hello")
    assert "after type" in result


@pytest.mark.asyncio
async def test_navigate(tools):
    resp = FakeResponse({"snapshot": "new page"})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.navigate("tab1", "https://example.com/page2")
    assert "new page" in result


@pytest.mark.asyncio
async def test_scroll(tools):
    resp = FakeResponse({"snapshot": "scrolled"})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.scroll("tab1", "down")
    assert "scrolled" in result


@pytest.mark.asyncio
async def test_screenshot(tools):
    resp = FakeResponse({"image": "base64data=="})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.screenshot("tab1")
    assert "base64data==" in result


@pytest.mark.asyncio
async def test_get_links(tools):
    resp = FakeResponse({
        "links": [
            {"text": "Example", "href": "https://example.com"},
            {"text": "Docs", "href": "https://docs.example.com"},
        ]
    })
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.get_links("tab1")
    assert "Example" in result
    assert "https://docs.example.com" in result


@pytest.mark.asyncio
async def test_close_tab(tools):
    resp = FakeResponse({"ok": True})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.close_tab("tab1")
    assert "tab1" in result
    assert "closed" in result.lower()


@pytest.mark.asyncio
async def test_list_tabs(tools):
    resp = FakeResponse({
        "tabs": [
            {"id": "tab1", "url": "https://example.com"},
            {"id": "tab2", "url": "https://docs.example.com"},
        ]
    })
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.list_tabs()
    assert "tab1" in result
    assert "tab2" in result


@pytest.mark.asyncio
async def test_list_tabs_empty(tools):
    resp = FakeResponse({"tabs": []})
    with patch("httpx.AsyncClient", return_value=FakeAsyncClient(resp)):
        result = await tools.list_tabs()
    assert "No open tabs" in result


# ---------------------------------------------------------------------------
# CamofoxServer — unit tests
# ---------------------------------------------------------------------------

@pytest.fixture
def server(tmp_path: Path) -> CamofoxServer:
    return CamofoxServer(install_dir=tmp_path / "camofox")


def test_is_installed_false(server: CamofoxServer):
    """Not installed by default."""
    assert server.is_installed() is False


def test_is_installed_true(server: CamofoxServer):
    """Returns True when both node and camofox binaries exist."""
    # Create fake binaries
    node = server._node_bin()
    node.parent.mkdir(parents=True, exist_ok=True)
    node.write_text("fake")

    camofox = server._camofox_bin()
    camofox.parent.mkdir(parents=True, exist_ok=True)
    camofox.write_text("fake")

    assert server.is_installed() is True


def test_check_node_not_installed(server: CamofoxServer):
    """Returns None when node is not installed."""
    assert server.check_node() is None


def test_check_node_installed(server: CamofoxServer):
    """Returns version string when node exists and responds."""
    node = server._node_bin()
    node.parent.mkdir(parents=True, exist_ok=True)
    node.write_text("fake")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="v22.0.0\n")
        version = server.check_node()

    assert version == "v22.0.0"


def test_node_bin_path(server: CamofoxServer):
    """Node binary path should be inside the node_env directory."""
    path = server._node_bin()
    assert "node_env" in str(path)


def test_npm_bin_path(server: CamofoxServer):
    """npm binary path should be inside the node_env directory."""
    path = server._npm_bin()
    assert "node_env" in str(path)


# ---------------------------------------------------------------------------
# Registry inclusion
# ---------------------------------------------------------------------------

def test_registry_includes_camofox(tmp_path: Path):
    """Camofox should appear in the tool registry after refresh."""
    from vandelay.tools.registry import ToolRegistry

    registry = ToolRegistry(cache_path=tmp_path / "tool_registry.json")
    registry.refresh()

    entry = registry.get("camofox")
    assert entry is not None
    assert entry.class_name == "CamofoxTools"
    assert entry.category == "browser"
    assert entry.module_path == "vandelay.tools.camofox"
