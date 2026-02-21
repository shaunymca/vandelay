"""CamoufoxTools — Agno Toolkit for anti-detect browsing via Camoufox + Playwright."""

from __future__ import annotations

import contextlib
import logging
import tempfile
from pathlib import Path

from agno.tools import Toolkit

logger = logging.getLogger("vandelay.tools.camoufox")


class CamoufoxTools(Toolkit):
    """Browser automation via Camoufox (anti-detect Firefox + Playwright).

    Camoufox is an open-source anti-detect browser built on Firefox.
    Uses the synchronous Camoufox API so functions are available in both
    sync and async agent contexts.
    """

    def __init__(self, headless: bool = True) -> None:
        super().__init__(name="camoufox")
        self._headless = headless
        self._browser = None  # Camoufox sync context manager
        self._context = None  # browser context
        self._pages: dict[str, object] = {}  # tab_id → Page
        self._counter = 0
        self.register(self.open_tab)
        self.register(self.navigate)
        self.register(self.get_page_content)
        self.register(self.click)
        self.register(self.type_text)
        self.register(self.screenshot)
        self.register(self.scroll)
        self.register(self.get_links)
        self.register(self.close_tab)
        self.register(self.list_tabs)

    def _ensure_browser(self) -> None:
        """Lazy-start the Camoufox browser on first use."""
        if self._context is not None:
            return

        from camoufox.sync_api import Camoufox

        self._browser = Camoufox(headless=self._headless)
        self._context = self._browser.__enter__()

    def _next_tab_id(self) -> str:
        self._counter += 1
        return f"tab{self._counter}"

    def open_tab(self, url: str) -> str:
        """Open a new browser tab and navigate to the given URL.

        Args:
            url: The URL to open.

        Returns:
            Tab ID and a text summary of the page content.
        """
        self._ensure_browser()
        page = self._context.new_page()
        tab_id = self._next_tab_id()
        self._pages[tab_id] = page

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            return f"Tab {tab_id} opened but navigation failed: {e}"

        title = page.title()
        try:
            text = page.inner_text("body")
            text = text[:3000].strip()
        except Exception:
            text = "(could not extract page text)"

        return f"Tab {tab_id} opened: {title}\n\n{text}"

    def navigate(self, tab_id: str, url: str) -> str:
        """Navigate an existing tab to a new URL.

        Args:
            tab_id: The tab identifier (e.g. 'tab1').
            url: The URL to navigate to.
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found. Use open_tab() first."

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            return f"Navigation failed: {e}"

        title = page.title()
        return f"Navigated {tab_id} to: {title} ({url})"

    def get_page_content(self, tab_id: str) -> str:
        """Get the text content of a tab's page.

        Args:
            tab_id: The tab identifier.
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."

        try:
            snapshot = page.accessibility.snapshot()
            if snapshot:
                return _format_a11y_tree(snapshot)
        except Exception:
            pass

        try:
            text = page.inner_text("body")
            return text[:5000].strip()
        except Exception as e:
            return f"Failed to get page content: {e}"

    def click(self, tab_id: str, selector: str) -> str:
        """Click an element by CSS selector or text.

        Args:
            tab_id: The tab identifier.
            selector: CSS selector or text selector (e.g. 'text=Submit').
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."

        try:
            page.click(selector, timeout=10000)
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception as e:
            return f"Click failed: {e}"

        title = page.title()
        return f"Clicked '{selector}' on {tab_id}. Page: {title}"

    def type_text(self, tab_id: str, selector: str, text: str) -> str:
        """Type text into an input element.

        Args:
            tab_id: The tab identifier.
            selector: CSS selector for the input element.
            text: The text to type.
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."

        try:
            page.fill(selector, text, timeout=10000)
        except Exception as e:
            return f"Type failed: {e}"

        return f"Typed '{text}' into '{selector}' on {tab_id}."

    def screenshot(self, tab_id: str, path: str | None = None) -> str:
        """Take a screenshot of a tab and save it to a file.

        Args:
            tab_id: The tab identifier.
            path: Optional file path to save the screenshot. If not provided,
                  saves to a temp file.

        Returns:
            Path to the saved screenshot PNG file.
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."

        try:
            if path:
                save_path = Path(path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                save_path = Path(tempfile.mktemp(suffix=".png", prefix="camoufox_"))
            page.screenshot(path=str(save_path), full_page=False)
            return f"Screenshot saved to: {save_path}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    def scroll(self, tab_id: str, direction: str = "down") -> str:
        """Scroll the page in a given direction.

        Args:
            tab_id: The tab identifier.
            direction: 'up', 'down', 'left', or 'right'.
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."

        scroll_map = {
            "down": "window.scrollBy(0, 600)",
            "up": "window.scrollBy(0, -600)",
            "left": "window.scrollBy(-600, 0)",
            "right": "window.scrollBy(600, 0)",
        }
        js = scroll_map.get(direction, scroll_map["down"])

        try:
            page.evaluate(js)
        except Exception as e:
            return f"Scroll failed: {e}"

        return f"Scrolled {direction} on {tab_id}."

    def get_links(self, tab_id: str) -> str:
        """Get all links on the current page.

        Args:
            tab_id: The tab identifier.
        """
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."

        try:
            links = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(el => ({text: el.innerText.trim(), href: el.href}))",
            )
            if not links:
                return "No links found on page."
            lines = [
                f"- {link['text']} → {link['href']}"
                for link in links if link.get("href")
            ]
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Failed to get links: {e}"

    def close_tab(self, tab_id: str) -> str:
        """Close a browser tab.

        Args:
            tab_id: The tab identifier.
        """
        page = self._pages.pop(tab_id, None)
        if not page:
            return f"Tab {tab_id} not found."

        with contextlib.suppress(Exception):
            page.close()

        return f"Tab {tab_id} closed."

    def list_tabs(self) -> str:
        """List all open browser tabs with their URLs."""
        if not self._pages:
            return "No open tabs."

        lines = []
        for tid, page in self._pages.items():
            try:
                url = page.url
            except Exception:
                url = "?"
            lines.append(f"- {tid}: {url}")
        return "\n".join(lines)

    def close(self) -> None:
        """Shut down the browser. Called during server shutdown."""
        for page in list(self._pages.values()):
            with contextlib.suppress(Exception):
                page.close()
        self._pages.clear()

        if self._browser is not None:
            with contextlib.suppress(Exception):
                self._browser.__exit__(None, None, None)
            self._browser = None
            self._context = None


def _format_a11y_tree(node: dict, indent: int = 0) -> str:
    """Format an accessibility tree snapshot into readable text."""
    parts = []
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")

    prefix = "  " * indent
    label_parts = [role]
    if name:
        label_parts.append(f'"{name}"')
    if value:
        label_parts.append(f"[{value}]")

    if role and role not in ("none", "generic"):
        parts.append(f"{prefix}{' '.join(label_parts)}")

    for child in node.get("children", []):
        parts.append(_format_a11y_tree(child, indent + 1))

    return "\n".join(parts)
