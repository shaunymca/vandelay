"""CamofoxTools — Agno Toolkit for the Camofox anti-detection browser server."""

from __future__ import annotations

from agno.tools import Toolkit

_DEFAULT_BASE_URL = "http://localhost:9377"


class CamofoxTools(Toolkit):
    """Browser automation via the Camofox REST API.

    Camofox provides anti-detection browsing with accessibility snapshots
    (500KB HTML → 5KB), stable element refs (e1, e2, …), and site macros.
    """

    def __init__(self, base_url: str = _DEFAULT_BASE_URL) -> None:
        super().__init__(name="camofox")
        self.base_url = base_url.rstrip("/")
        self.register(self.create_tab)
        self.register(self.snapshot)
        self.register(self.click)
        self.register(self.type_text)
        self.register(self.navigate)
        self.register(self.scroll)
        self.register(self.screenshot)
        self.register(self.get_links)
        self.register(self.close_tab)
        self.register(self.list_tabs)

    async def create_tab(self, url: str) -> str:
        """Open a new browser tab and navigate to the given URL."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.post("/tabs", json={"url": url})
            resp.raise_for_status()
            data = resp.json()
            tab_id = data.get("id", "unknown")
            snapshot = data.get("snapshot", "")
            return f"Tab {tab_id} opened.\n\n{snapshot}"

    async def snapshot(self, tab_id: str) -> str:
        """Get the accessibility snapshot of a tab (compact representation of the page)."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.get(f"/tabs/{tab_id}/snapshot")
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot", str(data))

    async def click(self, tab_id: str, ref: str) -> str:
        """Click an element by its reference ID (e.g. 'e1', 'e2')."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.post(f"/tabs/{tab_id}/click", json={"ref": ref})
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot", str(data))

    async def type_text(self, tab_id: str, ref: str, text: str) -> str:
        """Type text into an element by its reference ID."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.post(
                f"/tabs/{tab_id}/type", json={"ref": ref, "text": text}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot", str(data))

    async def navigate(self, tab_id: str, url: str) -> str:
        """Navigate a tab to a URL or site macro (e.g. '@google_search query')."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.post(f"/tabs/{tab_id}/navigate", json={"url": url})
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot", str(data))

    async def scroll(self, tab_id: str, direction: str = "down") -> str:
        """Scroll the page. Direction: 'up' or 'down'."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.post(
                f"/tabs/{tab_id}/scroll", json={"direction": direction}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot", str(data))

    async def screenshot(self, tab_id: str) -> str:
        """Take a screenshot of a tab. Returns base64-encoded image."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.get(f"/tabs/{tab_id}/screenshot")
            resp.raise_for_status()
            data = resp.json()
            return data.get("image", str(data))

    async def get_links(self, tab_id: str) -> str:
        """Get all links on the current page."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.get(f"/tabs/{tab_id}/links")
            resp.raise_for_status()
            data = resp.json()
            links = data.get("links", data)
            if isinstance(links, list):
                return "\n".join(
                    f"- {link.get('text', '')} → {link.get('href', '')}"
                    for link in links
                )
            return str(links)

    async def close_tab(self, tab_id: str) -> str:
        """Close a browser tab."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.delete(f"/tabs/{tab_id}")
            resp.raise_for_status()
            return f"Tab {tab_id} closed."

    async def list_tabs(self) -> str:
        """List all open browser tabs."""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.get("/tabs")
            resp.raise_for_status()
            data = resp.json()
            tabs = data.get("tabs", data)
            if isinstance(tabs, list):
                if not tabs:
                    return "No open tabs."
                lines = [f"- Tab {t.get('id', '?')}: {t.get('url', '?')}" for t in tabs]
                return "\n".join(lines)
            return str(tabs)
