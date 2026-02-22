"""CamoufoxTools — Agno Toolkit for anti-detect browsing via Camoufox + Playwright.

All browser operations run in a single dedicated thread (ThreadPoolExecutor with
max_workers=1). This is required because Playwright's sync API uses greenlets that
are bound to the thread they are created on. Agno calls tool functions via a thread
pool executor, which can use a different thread on each call — breaking Playwright.
Pinning to one thread fixes the "Cannot switch to a different thread" greenlet error.
"""

from __future__ import annotations

import contextlib
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Optional

from agno.tools import Toolkit

logger = logging.getLogger("vandelay.tools.camoufox")

# Timeout (seconds) for any single browser operation
_BROWSER_TIMEOUT = 60


class CamoufoxTools(Toolkit):
    """Browser automation via Camoufox (anti-detect Firefox + Playwright).

    Camoufox is an open-source anti-detect browser built on Firefox.
    Uses the synchronous Camoufox API pinned to a single dedicated thread
    so Playwright greenlets never cross thread boundaries.

    Default launch options (all configurable via configure_browser tool):
        headless=True, disable_coop=True, humanize=True, geoip=True

    Args:
        headless: Run browser headlessly (default True).
        disable_coop: Disable Cross-Origin-Opener-Policy. Required for
            passwordless login flows and CAPTCHA/Turnstile iframes (default True).
        humanize: Humanize cursor movement to bypass bot detection. Pass True
            to enable with default timing, or a float for max duration in seconds
            (default True).
        geoip: Auto-resolve geolocation, timezone, locale from IP (default True).
        block_images: Block all images for faster loading (default False).
        block_webrtc: Block WebRTC to prevent IP leaks (default False).
        os: OS fingerprint to emulate — 'windows', 'macos', 'linux', or a list
            to randomly pick from (default: random).
        proxy: Playwright proxy dict, e.g.
            {"server": "http://host:port", "username": "u", "password": "p"}.
        locale: Browser locale, e.g. 'en-US'.
    """

    def __init__(
        self,
        headless: bool = True,
        disable_coop: bool = True,
        humanize: bool | float = True,
        geoip: bool = True,
        block_images: bool = False,
        block_webrtc: bool = False,
        os: Optional[str | list[str]] = None,
        proxy: Optional[dict] = None,
        locale: Optional[str] = None,
    ) -> None:
        super().__init__(name="camoufox")
        # Launch config — agents can update these via configure_browser()
        self._launch_config: dict = {
            "headless": headless,
            "disable_coop": disable_coop,
            "humanize": humanize,
            "geoip": geoip,
            "block_images": block_images,
            "block_webrtc": block_webrtc,
        }
        if os is not None:
            self._launch_config["os"] = os
        if proxy is not None:
            self._launch_config["proxy"] = proxy
        if locale is not None:
            self._launch_config["locale"] = locale

        self._browser = None   # Camoufox sync context manager
        self._context = None   # browser context
        self._pages: dict[str, object] = {}  # tab_id → Page
        self._counter = 0
        # Single-thread executor: all Playwright calls must happen on the same thread
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="camoufox")

        # --- Browser lifecycle ---
        self.register(self.configure_browser)
        self.register(self.restart_browser)
        self.register(self.get_browser_config)
        # --- Tab management ---
        self.register(self.open_tab)
        self.register(self.navigate)
        self.register(self.close_tab)
        self.register(self.list_tabs)
        self.register(self.get_url)
        # --- Content extraction ---
        self.register(self.get_page_content)
        self.register(self.get_html)
        self.register(self.get_links)
        # --- Interaction ---
        self.register(self.click)
        self.register(self.type_text)
        self.register(self.scroll)
        self.register(self.execute_js)
        # --- Waiting ---
        self.register(self.wait_for_element)
        self.register(self.wait_for_url)
        # --- Capture ---
        self.register(self.screenshot)

    # ------------------------------------------------------------------
    # Internal helpers — always run inside the executor thread
    # ------------------------------------------------------------------

    def _run(self, fn, *args, **kwargs) -> str:
        """Submit *fn* to the browser thread and block until done."""
        try:
            future = self._executor.submit(fn, *args, **kwargs)
            return future.result(timeout=_BROWSER_TIMEOUT)
        except FuturesTimeoutError:
            return f"Browser operation timed out after {_BROWSER_TIMEOUT}s."
        except Exception as e:
            logger.exception("Browser thread error in %s", fn.__name__)
            return f"Browser error: {e}"

    def _ensure_browser(self) -> None:
        """Lazy-start the Camoufox browser. Must be called inside the executor thread."""
        if self._context is not None:
            return

        from camoufox.sync_api import Camoufox

        cfg = dict(self._launch_config)
        if cfg.get("disable_coop"):
            cfg["i_know_what_im_doing"] = True

        self._browser = Camoufox(**cfg)
        self._context = self._browser.__enter__()
        logger.info("Camoufox browser started (config: %s)", {k: v for k, v in cfg.items() if k != "proxy"})

    def _stop_browser(self) -> None:
        """Stop the browser. Must be called inside the executor thread."""
        for page in list(self._pages.values()):
            with contextlib.suppress(Exception):
                page.close()
        self._pages.clear()
        if self._browser is not None:
            with contextlib.suppress(Exception):
                self._browser.__exit__(None, None, None)
        self._browser = None
        self._context = None

    def _next_tab_id(self) -> str:
        self._counter += 1
        return f"tab{self._counter}"

    # ------------------------------------------------------------------
    # Browser lifecycle tools
    # ------------------------------------------------------------------

    def configure_browser(
        self,
        disable_coop: Optional[bool] = None,
        humanize: Optional[bool] = None,
        geoip: Optional[bool] = None,
        block_images: Optional[bool] = None,
        block_webrtc: Optional[bool] = None,
        os: Optional[str] = None,
        locale: Optional[str] = None,
        proxy_server: Optional[str] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
    ) -> str:
        """Configure browser launch options before starting or restart with new settings.

        Changes take effect on the next browser start. If the browser is already
        running, use restart_browser() to apply them immediately. Only pass the
        options you want to change — others keep their current values.

        Args:
            disable_coop: Disable Cross-Origin-Opener-Policy. Required for
                Turnstile CAPTCHA and passwordless login flows (recommended: True).
            humanize: Humanize cursor movement to bypass bot detection (recommended: True).
            geoip: Auto-resolve geolocation and timezone from IP address (recommended: True).
            block_images: Block all images for faster page loading.
            block_webrtc: Block WebRTC to prevent real IP leaks.
            os: OS fingerprint to emulate — 'windows', 'macos', or 'linux'.
            locale: Browser locale string, e.g. 'en-US', 'fr-FR'.
            proxy_server: Proxy server URL, e.g. 'http://host:8080' or 'socks5://host:1080'.
            proxy_username: Proxy authentication username.
            proxy_password: Proxy authentication password.

        Returns:
            Confirmation of the updated config.
        """
        if disable_coop is not None:
            self._launch_config["disable_coop"] = disable_coop
        if humanize is not None:
            self._launch_config["humanize"] = humanize
        if geoip is not None:
            self._launch_config["geoip"] = geoip
        if block_images is not None:
            self._launch_config["block_images"] = block_images
        if block_webrtc is not None:
            self._launch_config["block_webrtc"] = block_webrtc
        if os is not None:
            self._launch_config["os"] = os
        if locale is not None:
            self._launch_config["locale"] = locale
        if proxy_server is not None:
            proxy: dict = {"server": proxy_server}
            if proxy_username:
                proxy["username"] = proxy_username
            if proxy_password:
                proxy["password"] = proxy_password
            self._launch_config["proxy"] = proxy

        safe_cfg = {k: v for k, v in self._launch_config.items() if k != "proxy"}
        running = "Browser is running — call restart_browser() to apply changes." if self._context else "Changes will apply on next browser start."
        return f"Browser config updated: {safe_cfg}\n{running}"

    def get_browser_config(self) -> str:
        """Show the current browser launch configuration.

        Returns:
            Current Camoufox launch options (proxy credentials redacted).
        """
        safe_cfg = {k: v for k, v in self._launch_config.items() if k != "proxy"}
        if "proxy" in self._launch_config:
            safe_cfg["proxy"] = {"server": self._launch_config["proxy"].get("server", ""), "auth": "***"}
        status = "running" if self._context else "not started"
        tabs = list(self._pages.keys())
        return f"Browser status: {status}\nOpen tabs: {tabs or 'none'}\nConfig: {safe_cfg}"

    def restart_browser(self) -> str:
        """Restart the browser, applying any updated configuration.

        Closes all open tabs and restarts with the current config settings.
        Use this after configure_browser() to apply changes immediately.

        Returns:
            Confirmation that the browser restarted.
        """
        return self._run(self._restart_browser)

    def _restart_browser(self) -> str:
        self._stop_browser()
        self._ensure_browser()
        return "Browser restarted with updated config."

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def open_tab(self, url: str) -> str:
        """Open a new browser tab and navigate to the given URL.

        Args:
            url: The URL to open.

        Returns:
            Tab ID and a text summary of the page content.
        """
        return self._run(self._open_tab, url)

    def _open_tab(self, url: str) -> str:
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
            tab_id: The tab identifier returned by open_tab (e.g. 'tab1').
            url: The URL to navigate to.
        """
        return self._run(self._navigate, tab_id, url)

    def _navigate(self, tab_id: str, url: str) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found. Use open_tab() first."
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            return f"Navigation failed: {e}"
        return f"Navigated {tab_id} to: {page.title()} ({url})"

    def close_tab(self, tab_id: str) -> str:
        """Close a browser tab.

        Args:
            tab_id: The tab identifier.
        """
        return self._run(self._close_tab, tab_id)

    def _close_tab(self, tab_id: str) -> str:
        page = self._pages.pop(tab_id, None)
        if not page:
            return f"Tab {tab_id} not found."
        with contextlib.suppress(Exception):
            page.close()
        return f"Tab {tab_id} closed."

    def list_tabs(self) -> str:
        """List all open browser tabs with their current URLs."""
        return self._run(self._list_tabs)

    def _list_tabs(self) -> str:
        if not self._pages:
            return "No open tabs."
        lines = [f"- {tid}: {self._safe_url(page)}" for tid, page in self._pages.items()]
        return "\n".join(lines)

    def get_url(self, tab_id: str) -> str:
        """Get the current URL of a tab.

        Args:
            tab_id: The tab identifier.

        Returns:
            The current URL of the tab.
        """
        return self._run(self._get_url, tab_id)

    def _get_url(self, tab_id: str) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        return self._safe_url(page)

    def _safe_url(self, page) -> str:
        try:
            return page.url
        except Exception:
            return "?"

    # ------------------------------------------------------------------
    # Content extraction
    # ------------------------------------------------------------------

    def get_page_content(self, tab_id: str) -> str:
        """Get the text content of a tab's page via accessibility tree (preferred) or inner text.

        Args:
            tab_id: The tab identifier.
        """
        return self._run(self._get_page_content, tab_id)

    def _get_page_content(self, tab_id: str) -> str:
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
            return page.inner_text("body")[:5000].strip()
        except Exception as e:
            return f"Failed to get page content: {e}"

    def get_html(self, tab_id: str) -> str:
        """Get the raw HTML source of a tab's page.

        Args:
            tab_id: The tab identifier.

        Returns:
            The full HTML source of the page (truncated to 10000 chars).
        """
        return self._run(self._get_html, tab_id)

    def _get_html(self, tab_id: str) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        try:
            html = page.content()
            return html[:10000]
        except Exception as e:
            return f"Failed to get HTML: {e}"

    def get_links(self, tab_id: str) -> str:
        """Get all links on the current page.

        Args:
            tab_id: The tab identifier.
        """
        return self._run(self._get_links, tab_id)

    def _get_links(self, tab_id: str) -> str:
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
            lines = [f"- {l['text']} → {l['href']}" for l in links if l.get("href")]
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Failed to get links: {e}"

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def click(self, tab_id: str, selector: str) -> str:
        """Click an element by CSS selector or text.

        Args:
            tab_id: The tab identifier.
            selector: CSS selector or text selector (e.g. '#submit-btn', 'text=Login',
                '[data-testid=search]').
        """
        return self._run(self._click, tab_id, selector)

    def _click(self, tab_id: str, selector: str) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        try:
            page.click(selector, timeout=10000)
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception as e:
            return f"Click failed: {e}"
        return f"Clicked '{selector}' on {tab_id}. Page: {page.title()}"

    def type_text(self, tab_id: str, selector: str, text: str) -> str:
        """Type text into an input element.

        Args:
            tab_id: The tab identifier.
            selector: CSS selector for the input element.
            text: The text to type.
        """
        return self._run(self._type_text, tab_id, selector, text)

    def _type_text(self, tab_id: str, selector: str, text: str) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        try:
            page.fill(selector, text, timeout=10000)
        except Exception as e:
            return f"Type failed: {e}"
        return f"Typed into '{selector}' on {tab_id}."

    def scroll(self, tab_id: str, direction: str = "down") -> str:
        """Scroll the page in a given direction.

        Args:
            tab_id: The tab identifier.
            direction: 'up', 'down', 'left', or 'right'.
        """
        return self._run(self._scroll, tab_id, direction)

    def _scroll(self, tab_id: str, direction: str = "down") -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        scroll_map = {
            "down": "window.scrollBy(0, 600)",
            "up": "window.scrollBy(0, -600)",
            "left": "window.scrollBy(-600, 0)",
            "right": "window.scrollBy(600, 0)",
        }
        try:
            page.evaluate(scroll_map.get(direction, scroll_map["down"]))
        except Exception as e:
            return f"Scroll failed: {e}"
        return f"Scrolled {direction} on {tab_id}."

    def execute_js(self, tab_id: str, script: str) -> str:
        """Execute arbitrary JavaScript in a tab and return the result.

        Args:
            tab_id: The tab identifier.
            script: JavaScript code to execute. The return value is converted to a string.
                Example: 'document.title' or 'document.querySelector("#email").value'.

        Returns:
            The string result of the JS expression, or an error message.
        """
        return self._run(self._execute_js, tab_id, script)

    def _execute_js(self, tab_id: str, script: str) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        try:
            result = page.evaluate(script)
            return str(result) if result is not None else "(no return value)"
        except Exception as e:
            return f"JS execution failed: {e}"

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_for_element(
        self,
        tab_id: str,
        selector: str,
        timeout: int = 15,
    ) -> str:
        """Wait for an element to appear on the page.

        Use this after triggering actions that load content dynamically, such as
        submitting a login form and waiting for the dashboard to render.

        Args:
            tab_id: The tab identifier.
            selector: CSS selector to wait for (e.g. '#dashboard', '.welcome-message').
            timeout: Maximum seconds to wait (default 15).

        Returns:
            Confirmation that the element appeared, or a timeout error.
        """
        return self._run(self._wait_for_element, tab_id, selector, timeout)

    def _wait_for_element(self, tab_id: str, selector: str, timeout: int) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        try:
            page.wait_for_selector(selector, timeout=timeout * 1000)
            return f"Element '{selector}' appeared on {tab_id}."
        except Exception as e:
            return f"Timed out waiting for '{selector}': {e}"

    def wait_for_url(
        self,
        tab_id: str,
        url_pattern: str,
        timeout: int = 30,
    ) -> str:
        """Wait for the tab's URL to match a pattern (useful after redirects and OAuth flows).

        Args:
            tab_id: The tab identifier.
            url_pattern: URL substring or glob pattern to wait for
                (e.g. 'app.commonroom.io/home', '*/dashboard*').
            timeout: Maximum seconds to wait (default 30).

        Returns:
            The final URL when matched, or a timeout error.
        """
        return self._run(self._wait_for_url, tab_id, url_pattern, timeout)

    def _wait_for_url(self, tab_id: str, url_pattern: str, timeout: int) -> str:
        page = self._pages.get(tab_id)
        if not page:
            return f"Tab {tab_id} not found."
        try:
            page.wait_for_url(f"**{url_pattern}**" if "*" not in url_pattern else url_pattern,
                              timeout=timeout * 1000)
            return f"URL matched '{url_pattern}': {page.url}"
        except Exception as e:
            return f"Timed out waiting for URL '{url_pattern}': {e}"

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def screenshot(self, tab_id: str, path: Optional[str] = None) -> str:
        """Take a screenshot of a tab and save it to a file.

        Args:
            tab_id: The tab identifier.
            path: Optional file path to save the screenshot. Defaults to a temp file.

        Returns:
            Path to the saved screenshot PNG file.
        """
        return self._run(self._screenshot, tab_id, path)

    def _screenshot(self, tab_id: str, path: Optional[str] = None) -> str:
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

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Shut down the browser and executor. Called during server shutdown."""
        with contextlib.suppress(Exception):
            future = self._executor.submit(self._stop_browser)
            future.result(timeout=10)
        self._executor.shutdown(wait=False)


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
