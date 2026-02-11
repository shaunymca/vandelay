"""Tool registry — discovers and caches all available Agno tools."""

from __future__ import annotations

import importlib
import json
import pkgutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vandelay.config.constants import TOOL_REGISTRY_FILE

# Modules that are internal/base classes, not user-facing tools
_INTERNAL_MODULES = frozenset({
    "decorator",
    "function",
    "models",
    "streamlit",
    "tool_registry",
    "toolkit",
})

# Base Toolkit methods to skip when extracting descriptions
_BASE_METHODS = frozenset({
    "close", "connect", "get_async_functions", "get_functions", "register",
})

# Hand-curated category map — everything else defaults to "other"
_CATEGORY_MAP: dict[str, str] = {
    # Web search & scraping
    "baidusearch": "search", "bravesearch": "search", "crawl4ai": "search",
    "duckduckgo": "search", "exa": "search", "firecrawl": "search",
    "jina": "search", "linkup": "search", "newspaper": "search",
    "newspaper4k": "search", "oxylabs": "search", "parallel": "search",
    "scrapegraph": "search", "searxng": "search", "seltz": "search",
    "serpapi": "search", "serper": "search", "spider": "search",
    "tavily": "search", "trafilatura": "search", "valyu": "search",
    "webbrowser": "search", "websearch": "search", "website": "search",
    "webtools": "search",
    # Browser
    "agentql": "browser", "browserbase": "browser", "camofox": "browser",
    # File & code
    "file": "filesystem", "file_generation": "filesystem",
    "local_file_system": "filesystem", "csv_toolkit": "filesystem",
    "python": "code", "shell": "system",
    # Database
    "duckdb": "database", "google_bigquery": "database", "neo4j": "database",
    "pandas": "data", "postgres": "database", "redshift": "database",
    "sql": "database",
    # AI / generation
    "cartesia": "ai", "dalle": "ai", "eleven_labs": "ai", "fal": "ai",
    "lumalab": "ai", "mlx_transcribe": "ai", "models_labs": "ai",
    "moviepy_video": "ai", "nano_banana": "ai", "openai": "ai",
    "opencv": "ai", "replicate": "ai", "desi_vocal": "ai",
    # Communication
    "discord": "messaging", "email": "messaging", "gmail": "messaging",
    "resend": "messaging", "slack": "messaging", "telegram": "messaging",
    "twilio": "messaging", "webex": "messaging", "whatsapp": "messaging",
    # Project management
    "clickup": "productivity", "confluence": "productivity",
    "jira": "productivity", "linear": "productivity", "notion": "productivity",
    "todoist": "productivity", "trello": "productivity", "zendesk": "productivity",
    # Social
    "giphy": "social", "hackernews": "social", "reddit": "social",
    "unsplash": "social", "wikipedia": "knowledge", "x": "social",
    "youtube": "social",
    # Finance
    "financial_datasets": "finance", "openbb": "finance",
    "shopify": "finance", "yfinance": "finance",
    # Cloud / DevOps
    "airflow": "devops", "apify": "devops", "aws_lambda": "cloud",
    "aws_ses": "cloud", "bitbucket": "devops", "brightdata": "devops",
    "daytona": "devops", "docker": "devops", "e2b": "devops",
    "github": "devops",
    # Calendar
    "calcom": "calendar", "googlecalendar": "calendar", "zoom": "calendar",
    # Google
    "google_drive": "google", "google_maps": "google",
    "googlesheets": "google",
    # Agent infra
    "knowledge": "agent", "mem0": "agent", "memory": "agent",
    "zep": "agent", "reasoning": "agent", "workflow": "agent",
    "user_control_flow": "agent",
    # Misc
    "api": "utility", "calculator": "utility", "sleep": "utility",
    "visualization": "utility", "mcp": "integration", "mcp_toolbox": "integration",
    "evm": "blockchain", "spotify": "media", "brandfetch": "marketing",
    "arxiv": "research", "pubmed": "research", "openweather": "weather",
}

# Known pip dependencies per tool module
_PIP_DEPS: dict[str, list[str]] = {
    "baidusearch": ["baidusearch"],
    "bravesearch": ["brave-search"],
    "crawl4ai": ["crawl4ai"],
    "duckduckgo": ["ddgs"],
    "exa": ["exa_py"],
    "firecrawl": ["firecrawl-py"],
    "linkup": ["linkup-sdk"],
    "newspaper": ["newspaper3k", "lxml_html_clean"],
    "newspaper4k": ["newspaper4k", "lxml_html_clean"],
    "oxylabs": ["oxylabs"],
    "scrapegraph": ["scrapegraph-py"],
    "seltz": ["seltz"],
    "serpapi": ["google-search-results"],
    "serper": ["requests"],
    "spider": ["spider-client"],
    "tavily": ["tavily-python"],
    "trafilatura": ["trafilatura"],
    "valyu": ["valyu"],
    "websearch": ["ddgs"],
    "agentql": ["agentql"],
    "browserbase": ["browserbase"],
    "duckdb": ["duckdb"],
    "google_bigquery": ["google-cloud-bigquery"],
    "neo4j": ["neo4j"],
    "pandas": ["pandas"],
    "postgres": ["psycopg-binary"],
    "redshift": ["redshift-connector"],
    "cartesia": ["cartesia"],
    "dalle": ["openai"],
    "eleven_labs": ["elevenlabs"],
    "fal": ["fal-client"],
    "lumalab": ["lumaai"],
    "mlx_transcribe": ["mlx-whisper"],
    "models_labs": ["requests"],
    "moviepy_video": ["moviepy", "ffmpeg"],
    "nano_banana": ["google-genai", "Pillow"],
    "openai": ["openai"],
    "opencv": ["opencv-python"],
    "replicate": ["replicate"],
    "desi_vocal": ["requests"],
    "discord": ["requests"],
    "gmail": ["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"],
    "resend": ["resend"],
    "slack": ["slack-sdk"],
    "twilio": ["twilio"],
    "webex": ["webexpythonsdk"],
    "clickup": ["requests"],
    "confluence": ["requests"],
    "jira": ["jira"],
    "linear": ["requests"],
    "notion": ["notion-client"],
    "todoist": ["todoist-api-python"],
    "trello": ["py-trello"],
    "zendesk": ["requests"],
    "reddit": ["praw"],
    "wikipedia": ["wikipedia"],
    "x": ["tweepy"],
    "youtube": ["youtube_transcript_api"],
    "financial_datasets": ["requests"],
    "openbb": ["openbb"],
    "yfinance": ["yfinance"],
    "apify": ["requests"],
    "aws_lambda": ["boto3"],
    "aws_ses": ["boto3"],
    "bitbucket": ["requests"],
    "brightdata": ["requests"],
    "daytona": ["daytona"],
    "docker": ["docker"],
    "e2b": ["e2b_code_interpreter"],
    "github": ["pygithub"],
    "calcom": ["requests", "pytz"],
    "googlecalendar": ["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"],
    "zoom": ["requests"],
    "google_drive": ["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"],
    "google_maps": ["googlemaps", "google-maps-places"],
    "googlesheets": ["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"],
    "mem0": ["mem0ai"],
    "zep": ["zep-cloud"],
    "evm": ["web3"],
    "arxiv": ["arxiv"],
    "mcp": ["mcp"],
    "mcp_toolbox": ["mcp"],
    "openweather": ["requests"],
    "api": ["requests"],
}

# Custom (non-agno) tools shipped with vandelay
_CUSTOM_TOOLS: dict[str, dict[str, Any]] = {
    "camofox": {
        "module_path": "vandelay.tools.camofox",
        "class_name": "CamofoxTools",
        "description": (
            "Anti-detection browser with accessibility snapshots and stable element refs."
            " Methods: create_tab, snapshot, click, type_text, navigate, scroll,"
            " screenshot, get_links, close_tab, list_tabs"
        ),
        "category": "browser",
        "pip_dependencies": [],  # npm-managed, not pip
    },
}


@dataclass
class ToolEntry:
    """Metadata about a single Agno tool."""

    name: str
    module_path: str  # e.g. "agno.tools.shell"
    class_name: str  # e.g. "ShellTools"
    description: str = ""
    category: str = "other"
    pip_dependencies: list[str] = field(default_factory=list)
    is_builtin: bool = True  # True = no extra pip install needed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolEntry:
        return cls(**data)


@dataclass
class RegistryCache:
    """Serializable registry with metadata."""

    tools: dict[str, ToolEntry]
    refreshed_at: str  # ISO timestamp
    agno_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "refreshed_at": self.refreshed_at,
            "agno_version": self.agno_version,
            "tools": {k: v.to_dict() for k, v in self.tools.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryCache:
        tools = {
            k: ToolEntry.from_dict(v) for k, v in data.get("tools", {}).items()
        }
        return cls(
            tools=tools,
            refreshed_at=data.get("refreshed_at", ""),
            agno_version=data.get("agno_version", ""),
        )


class ToolRegistry:
    """Discovers, caches, and provides access to all available Agno tools."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self._cache_path = cache_path or TOOL_REGISTRY_FILE
        self._cache: RegistryCache | None = None

    @property
    def tools(self) -> dict[str, ToolEntry]:
        """All known tools. Loads from cache if not yet in memory."""
        if self._cache is None:
            self._load_or_refresh()
        return self._cache.tools  # type: ignore[union-attr]

    @property
    def refreshed_at(self) -> str:
        if self._cache is None:
            self._load_or_refresh()
        return self._cache.refreshed_at  # type: ignore[union-attr]

    def _load_or_refresh(self) -> None:
        """Load from disk cache, or discover + cache if no cache exists."""
        if self._cache_path.exists():
            try:
                data = json.loads(self._cache_path.read_text(encoding="utf-8"))
                self._cache = RegistryCache.from_dict(data)
                return
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        self.refresh()

    def refresh(self) -> int:
        """Re-discover all tools from the installed agno package. Returns count."""
        tools: dict[str, ToolEntry] = {}
        agno_version = ""

        try:
            import agno
            agno_version = getattr(agno, "__version__", "unknown")
        except ImportError:
            pass

        try:
            import agno.tools as agno_tools_pkg

            for _importer, module_name, _is_pkg in pkgutil.iter_modules(agno_tools_pkg.__path__):
                if module_name in _INTERNAL_MODULES:
                    continue

                entry = self._discover_module(module_name)
                if entry:
                    tools[entry.name] = entry

        except ImportError:
            pass

        # Merge custom (non-agno) tools shipped with vandelay
        for name, info in _CUSTOM_TOOLS.items():
            if name not in tools:
                tools[name] = ToolEntry(
                    name=name,
                    module_path=info["module_path"],
                    class_name=info["class_name"],
                    description=info.get("description", ""),
                    category=info.get("category", _CATEGORY_MAP.get(name, "other")),
                    pip_dependencies=info.get("pip_dependencies", []),
                    is_builtin=len(info.get("pip_dependencies", [])) == 0,
                )

        self._cache = RegistryCache(
            tools=tools,
            refreshed_at=datetime.now(UTC).isoformat(),
            agno_version=agno_version,
        )
        self._save()
        return len(tools)

    def _discover_module(self, module_name: str) -> ToolEntry | None:
        """Try to import a tool module and find its main Toolkit class."""
        full_path = f"agno.tools.{module_name}"

        # Find the main class name (and optionally the class object) by trying to import
        class_name, cls = self._find_class(full_path, module_name)
        if not class_name:
            return None

        pip_deps = _PIP_DEPS.get(module_name, [])
        category = _CATEGORY_MAP.get(module_name, "other")
        description = self._extract_description(cls) if cls else ""

        return ToolEntry(
            name=module_name,
            module_path=full_path,
            class_name=class_name,
            description=description,
            category=category,
            pip_dependencies=pip_deps,
            is_builtin=len(pip_deps) == 0,
        )

    def _find_class(self, full_path: str, module_name: str) -> tuple[str | None, type | None]:
        """Try to find the main Toolkit class in a module.

        Returns (class_name, class_object). class_object is None if the module
        could not be imported (missing deps).
        """
        # First, try importing the module
        try:
            mod = importlib.import_module(full_path)
            # Look for classes ending in "Tools" (the Agno convention)
            candidates = [
                name for name in dir(mod)
                if name.endswith("Tools") and not name.startswith("_")
            ]
            if candidates:
                return candidates[0], getattr(mod, candidates[0], None)

            # Some use singular names or other patterns
            candidates = [
                name for name in dir(mod)
                if not name.startswith("_")
                and name[0].isupper()
                and name not in ("Toolkit", "Tool", "Field", "BaseModel")
            ]
            if candidates:
                return candidates[0], getattr(mod, candidates[0], None)

        except Exception:
            # Module couldn't be imported (missing deps) — fall back to name convention
            pass

        # Convention-based fallback: shell → ShellTools
        parts = module_name.split("_")
        class_guess = "".join(p.capitalize() for p in parts) + "Tools"
        return class_guess, None

    @staticmethod
    def _extract_description(cls: type) -> str:
        """Build a description from a tool class's docstring and method docstrings."""
        import inspect

        parts: list[str] = []

        # Class-level docstring
        if cls.__doc__:
            parts.append(cls.__doc__.strip())

        # Collect tool-specific methods (skip base Toolkit inherited ones)
        methods: list[str] = []
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_") or name in _BASE_METHODS:
                continue
            doc = (method.__doc__ or "").strip()
            # Take only the first line of the docstring
            first_line = doc.split("\n")[0] if doc else ""
            if first_line:
                methods.append(f"{name} — {first_line}")
            else:
                methods.append(name)

        if methods:
            parts.append("Methods: " + "; ".join(methods))

        return " | ".join(parts) if parts else ""

    def _save(self) -> None:
        """Persist registry cache to disk."""
        if self._cache is None:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps(self._cache.to_dict(), indent=2),
            encoding="utf-8",
        )

    def get(self, name: str) -> ToolEntry | None:
        """Get a tool entry by name."""
        return self.tools.get(name)

    def search(self, query: str) -> list[ToolEntry]:
        """Search tools by name or category."""
        q = query.lower()
        return [
            t for t in self.tools.values()
            if q in t.name.lower() or q in t.category.lower()
        ]

    def by_category(self) -> dict[str, list[ToolEntry]]:
        """Group tools by category."""
        result: dict[str, list[ToolEntry]] = {}
        for tool in self.tools.values():
            result.setdefault(tool.category, []).append(tool)
        return result

    def builtin_tools(self) -> list[ToolEntry]:
        """Tools that need no extra pip install."""
        return [t for t in self.tools.values() if t.is_builtin]
