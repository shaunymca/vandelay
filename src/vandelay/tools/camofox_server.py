"""CamofoxServer — manages the isolated Node.js environment and camofox-browser subprocess."""

from __future__ import annotations

import asyncio
import logging
import platform
import subprocess
import sys
from pathlib import Path

from vandelay.config.constants import VANDELAY_HOME

logger = logging.getLogger("vandelay.tools.camofox_server")

_DEFAULT_INSTALL_DIR = VANDELAY_HOME / "camofox"
_NODE_VERSION = "22.22.0"  # Node 22 LTS — nodeenv requires full version
_NPM_PACKAGE = "@anthropic-ai/camofox-browser"
_HEALTH_URL = "http://localhost:9377/health"
_HEALTH_TIMEOUT = 30  # seconds
_HEALTH_POLL_INTERVAL = 1  # seconds


class CamofoxServer:
    """Manages the Camofox browser server lifecycle.

    Install time: creates an isolated Node.js env via nodeenv, then npm-installs
    the camofox-browser package. Runtime: spawns it as a subprocess and polls
    /health until ready.
    """

    def __init__(self, install_dir: Path | str | None = None) -> None:
        self.install_dir = Path(install_dir or _DEFAULT_INSTALL_DIR)
        self._process: asyncio.subprocess.Process | None = None

    # --- Path helpers ---

    @property
    def _node_env_dir(self) -> Path:
        return self.install_dir / "node_env"

    def _node_bin(self) -> Path:
        """Path to the managed node binary."""
        if platform.system() == "Windows":
            return self._node_env_dir / "Scripts" / "node.exe"
        return self._node_env_dir / "bin" / "node"

    def _npm_bin(self) -> Path:
        """Path to the managed npm binary."""
        if platform.system() == "Windows":
            return self._node_env_dir / "Scripts" / "npm.cmd"
        return self._node_env_dir / "bin" / "npm"

    def _npx_bin(self) -> Path:
        """Path to the managed npx binary."""
        if platform.system() == "Windows":
            return self._node_env_dir / "Scripts" / "npx.cmd"
        return self._node_env_dir / "bin" / "npx"

    def _camofox_bin(self) -> Path:
        """Path to the camofox-browser executable."""
        if platform.system() == "Windows":
            return self.install_dir / "node_modules" / ".bin" / "camofox-browser.cmd"
        return self.install_dir / "node_modules" / ".bin" / "camofox-browser"

    # --- State checks ---

    def is_installed(self) -> bool:
        """Check if nodeenv and camofox-browser npm package are installed."""
        return self._node_bin().exists() and self._camofox_bin().exists()

    def check_node(self) -> str | None:
        """Check managed Node.js version. Returns version string or None."""
        node = self._node_bin()
        if not node.exists():
            return None
        try:
            result = subprocess.run(
                [str(node), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, OSError):
            return None

    # --- Install ---

    def install(self) -> None:
        """Create isolated Node.js env and install camofox-browser.

        This is called during onboarding or `tools enable camofox`, not at runtime.
        """
        self.install_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Create nodeenv if it doesn't exist
        if not self._node_bin().exists():
            logger.info("Creating isolated Node.js %s environment...", _NODE_VERSION)
            self._create_nodeenv()

        # Step 2: npm install camofox-browser
        if not self._camofox_bin().exists():
            logger.info("Installing camofox-browser via npm...")
            self._npm_install()

        logger.info("Camofox installation complete.")

    def _create_nodeenv(self) -> None:
        """Create an isolated Node.js environment using nodeenv."""
        try:
            import nodeenv  # noqa: F401 — verify it's importable
        except ImportError:
            raise RuntimeError(
                "nodeenv is not installed. Run: uv add nodeenv"
            ) from None

        result = subprocess.run(
            [
                sys.executable, "-m", "nodeenv",
                "--node", _NODE_VERSION,
                "--prebuilt",
                str(self._node_env_dir),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"nodeenv creation failed:\n{result.stderr.strip()}"
            )

    def _npm_install(self) -> None:
        """Install camofox-browser into the install directory."""
        import os

        npm = self._npm_bin()
        if not npm.exists():
            raise RuntimeError(f"npm not found at {npm}")

        # Put managed Node.js on PATH so npm's #!/usr/bin/env node shebang works
        env = os.environ.copy()
        node_dir = str(self._node_bin().parent)
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

        result = subprocess.run(
            [str(npm), "install", _NPM_PACKAGE],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(self.install_dir),
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"npm install failed:\n{result.stderr.strip()}"
            )

    # --- Runtime lifecycle ---

    async def start(self) -> None:
        """Start the camofox-browser subprocess and wait until healthy."""
        if self._process is not None:
            logger.warning("Camofox server already running (pid=%s)", self._process.pid)
            return

        if not self.is_installed():
            raise RuntimeError(
                "Camofox is not installed. Run: vandelay tools enable camofox"
            )

        camofox_bin = self._camofox_bin()
        node_bin = self._node_bin()

        logger.info("Starting camofox-browser server...")

        # Build environment with managed Node.js in PATH
        import os
        env = os.environ.copy()
        node_dir = str(node_bin.parent)
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

        self._process = await asyncio.create_subprocess_exec(
            str(camofox_bin),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.install_dir),
            env=env,
        )

        logger.info("Camofox process started (pid=%s), polling health...", self._process.pid)

        # Poll /health until ready
        await self._wait_for_health()
        logger.info("Camofox server is ready.")

    async def _wait_for_health(self) -> None:
        """Poll the health endpoint until it responds or timeout."""
        import httpx

        deadline = asyncio.get_event_loop().time() + _HEALTH_TIMEOUT

        while asyncio.get_event_loop().time() < deadline:
            # Check if process died
            if self._process and self._process.returncode is not None:
                stderr = ""
                if self._process.stderr:
                    stderr = (await self._process.stderr.read()).decode(errors="replace")
                raise RuntimeError(
                    f"Camofox process exited with code {self._process.returncode}:\n{stderr}"
                )

            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(_HEALTH_URL)
                    if resp.status_code == 200:
                        return
            except (httpx.ConnectError, httpx.ReadTimeout, OSError):
                pass

            await asyncio.sleep(_HEALTH_POLL_INTERVAL)

        # Timeout — kill the process
        await self.stop()
        raise RuntimeError(
            f"Camofox server did not become healthy within {_HEALTH_TIMEOUT}s"
        )

    async def stop(self) -> None:
        """Terminate the camofox-browser subprocess."""
        if self._process is None:
            return

        pid = self._process.pid
        logger.info("Stopping camofox server (pid=%s)...", pid)

        try:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except TimeoutError:
                logger.warning("Camofox didn't exit gracefully, killing...")
                self._process.kill()
                await self._process.wait()
        except ProcessLookupError:
            pass  # Already exited

        self._process = None
        logger.info("Camofox server stopped.")
