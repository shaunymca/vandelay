"""Build the system prompt from workspace templates."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from vandelay.workspace.manager import get_template_content

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


def build_personality_brief(workspace_dir: Path | None = None) -> str:
    """Extract Core Truths and Vibe sections from SOUL.md for member injection.

    Returns a short personality brief (~6 lines) that gives specialist agents
    a consistent voice even when they respond directly (route mode).
    """
    soul = get_template_content("SOUL.md", workspace_dir)
    if not soul:
        return ""

    sections_to_extract = ("## Core Truths", "## Vibe")
    lines: list[str] = []
    capturing = False

    for line in soul.splitlines():
        if line.startswith("## "):
            capturing = line.strip() in sections_to_extract
        if capturing:
            lines.append(line)

    return "\n".join(lines).strip() if lines else ""


def _build_tool_catalog(settings: Settings) -> str:
    """Generate a markdown section listing all available tools by category.

    Marks which tools are currently enabled so the agent knows its own state.
    """
    from vandelay.tools.registry import ToolRegistry

    registry = ToolRegistry()
    by_cat = registry.by_category()
    if not by_cat:
        return ""

    enabled = set(settings.enabled_tools)

    # Only list enabled tools in the prompt to keep it lean.
    # The agent can use `list_available_tools` to discover others.
    enabled_entries = []
    for entries in by_cat.values():
        for entry in entries:
            if entry.name in enabled:
                enabled_entries.append(entry)

    if not enabled_entries:
        return ""

    lines: list[str] = [
        "# Your Enabled Tools",
        "",
        "These tools are registered as direct function calls — their full method",
        "signatures, parameters, and descriptions are already in your function",
        "definitions. **Do not investigate or look up tool methods.** Just call them.",
        "",
    ]

    for entry in sorted(enabled_entries, key=lambda e: (e.category, e.name)):
        lines.append(f"- **{entry.name}** [{entry.category}]")

    lines.append("")
    lines.append(
        "To discover and enable more tools, use `list_available_tools`."
    )
    lines.append("")
    return "\n".join(lines)


def _build_credentials_summary() -> str:
    """Scan configured credentials and return a status summary for the prompt.

    This prevents agents from asking users to set up credentials that
    already exist.
    """
    from vandelay.config.constants import VANDELAY_HOME

    lines: list[str] = [
        "# Your Configured Credentials",
        "",
        "These credentials are already set up. **Do NOT ask the user to configure them.**",
        "Just call the tool directly.",
        "",
    ]

    # Check Google OAuth token
    google_token = VANDELAY_HOME / "google_token.json"
    if google_token.exists():
        lines.append(
            "- **Google OAuth**: \u2705 authenticated (Gmail, Calendar, Drive, Sheets)"
        )
    else:
        lines.append(
            "- **Google OAuth**: \u274c not set up "
            "(user can run `vandelay tools auth-google`)"
        )

    # Scan .env for known API key patterns
    env_file = VANDELAY_HOME / ".env"
    configured_keys: set[str] = set()
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key = line.partition("=")[0].strip()
                if key:
                    configured_keys.add(key.upper())
        except OSError:
            pass

    # Common API keys to report on
    _KEY_LABELS = {
        "ANTHROPIC_API_KEY": "Anthropic",
        "OPENAI_API_KEY": "OpenAI",
        "GOOGLE_API_KEY": "Google AI",
        "TAVILY_API_KEY": "Tavily (web search)",
        "GITHUB_TOKEN": "GitHub",
        "OPENROUTER_API_KEY": "OpenRouter",
    }
    for key, label in _KEY_LABELS.items():
        if key in configured_keys:
            lines.append(f"- **{label}**: \u2705 configured")

    lines.append("")
    lines.append(
        "If a tool fails with an auth error, check `~/.vandelay/.env` — "
        "do not ask the user to set up credentials that are already listed above."
    )
    lines.append("")
    return "\n".join(lines)


def build_system_prompt(
    agent_name: str = "Art",
    workspace_dir: Path | None = None,
    settings: Settings | None = None,
) -> str:
    """Assemble the full system prompt from workspace markdown files.

    The prompt is structured as:
      1. Soul (personality, values)
      2. User profile (who you're helping)
      3. Agent behavior guidelines
      4. Tool usage guidelines
      5. Available tool catalog (auto-generated)
      6. Curated memory (long-term)
      7. Bootstrap (first-run only, if present)
    """
    sections: list[str] = []

    # Agent identity preamble + current date/time so the agent never
    # falls back to its training-cutoff date for scheduling tasks.
    from datetime import datetime

    now = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    sections.append(f"Your name is **{agent_name}**.\n\nCurrent date and time: {now}")

    soul = get_template_content("SOUL.md", workspace_dir)
    if soul:
        sections.append(soul)

    user = get_template_content("USER.md", workspace_dir)
    if user:
        sections.append(user)

    agents = get_template_content("AGENTS.md", workspace_dir)
    if agents:
        sections.append(agents)

    tools = get_template_content("TOOLS.md", workspace_dir)
    if tools:
        sections.append(tools)

    # Dynamic tool catalog
    if settings is not None:
        catalog = _build_tool_catalog(settings)
        if catalog:
            sections.append(catalog)

    # Dynamic credentials summary — prevents agents from asking users
    # to set up credentials that are already configured.
    creds = _build_credentials_summary()
    if creds:
        sections.append(creds)

    heartbeat = get_template_content("HEARTBEAT.md", workspace_dir)
    if heartbeat:
        sections.append(heartbeat)

    # Bootstrap is included once and then auto-deleted so it never
    # appears again. We read directly (no shipped-default fallback)
    # because absence of the file means it has already been used.
    if workspace_dir:
        bootstrap_path = workspace_dir / "BOOTSTRAP.md"
        if bootstrap_path.exists():
            sections.append(bootstrap_path.read_text(encoding="utf-8"))
            with contextlib.suppress(OSError):
                bootstrap_path.unlink()

    return "\n\n---\n\n".join(sections)


# Sections to keep in the slim AGENTS.md for the team leader.
# The leader doesn't need "Working Directory" or "Delegation" — those are
# replaced by the dynamic member roster.
_LEADER_AGENTS_SECTIONS = {
    "## Workspace Files",
    "## Safety Rules",
    "## Response Style",
    "## Error Handling",
}


def _build_agents_slim(workspace_dir: Path | None = None) -> str:
    """Load AGENTS.md and keep only sections relevant to the team leader.

    Drops "Working Directory" and "Delegation" (replaced by the member roster).
    """
    agents = get_template_content("AGENTS.md", workspace_dir)
    if not agents:
        return ""

    # Split into sections by ## headings
    kept: list[str] = []
    capturing = False

    for line in agents.splitlines():
        if line.startswith("## "):
            capturing = line.strip() in _LEADER_AGENTS_SECTIONS
        if capturing:
            kept.append(line)

    return "\n".join(kept).strip() if kept else ""


def _build_member_roster(settings: Settings) -> str:
    """Generate a markdown roster of team members from config."""
    from vandelay.agents.factory import _resolve_member
    from vandelay.tools.registry import ToolRegistry

    members = settings.team.members
    if not members:
        return ""

    # Load tool descriptions for the routing table
    registry = ToolRegistry()
    tool_descs: dict[str, str] = {}
    for entries in registry.by_category().values():
        for entry in entries:
            if entry.name in settings.enabled_tools:
                # Short label: first method description or category
                desc = entry.description or ""
                # Extract first method summary if description starts with "Methods:"
                if desc.startswith("Methods:"):
                    first = desc.split(";")[0].replace("Methods: ", "")
                    tool_descs[entry.name] = first.strip()
                else:
                    tool_descs[entry.name] = desc[:80] if desc else entry.category

    lines: list[str] = [
        "# Your Team",
        "",
        "Delegate tasks to the best member based on their role and expertise first,",
        "then verify they have the tools needed for the task.",
        "",
    ]

    # Member table with tool descriptions
    for entry in members:
        mc = _resolve_member(entry)
        name = mc.name
        role = mc.role or "(no role)"
        model_str = (
            f"{mc.model_provider} / {mc.model_id}"
            if mc.model_provider and mc.model_id
            else "inherited"
        )
        tool_list = []
        for t in mc.tools:
            desc = tool_descs.get(t, "")
            tool_list.append(f"{t} ({desc})" if desc else t)
        tools_str = ", ".join(tool_list) if tool_list else "none"
        lines.append(f"### {name}")
        lines.append(f"**Role**: {role}  ")
        lines.append(f"**Model**: {model_str}  ")
        lines.append(f"**Tools**: {tools_str}")
        lines.append("")

    # Build tool routing table: capability → member(s)
    tool_to_members: dict[str, list[str]] = {}
    for entry in members:
        mc = _resolve_member(entry)
        for t in mc.tools:
            tool_to_members.setdefault(t, []).append(mc.name)

    # Group by category for cleaner routing
    cat_routing: dict[str, dict[str, list[str]]] = {}
    for entries in registry.by_category().values():
        for entry in entries:
            if entry.name in tool_to_members:
                cat = entry.category or "other"
                cat_routing.setdefault(cat, {})[entry.name] = tool_to_members[
                    entry.name
                ]

    if cat_routing:
        lines.extend([
            "## Tool Routing",
            "",
            "When a task requires specific tools, delegate to a member who has them.",
            "If multiple members have the tool, prefer the one whose role fits best.",
            "",
            "| Tool | Category | Available On |",
            "|------|----------|-------------|",
        ])
        for cat in sorted(cat_routing):
            for tool_name in sorted(cat_routing[cat]):
                member_names = ", ".join(cat_routing[cat][tool_name])
                lines.append(f"| {tool_name} | {cat} | {member_names} |")
        lines.append("")

    lines.extend([
        "## Delegation Rules",
        "1. **Role first**: choose the member whose expertise matches the task",
        "2. **Verify tools**: confirm the chosen member has the tools the task needs "
        "(check the Tool Routing table above)",
        "3. **Never guess**: if a task needs a Google tool (gmail, sheets, calendar, "
        "drive), only delegate to a member that has it — do NOT send it to a member "
        "who would need to use shell commands or python as a workaround",
        "4. If no member fits, handle it yourself or suggest the user add a specialist",
        "5. Synthesize member results into a single clear response — "
        "do not pass member output through verbatim",
        "6. If a member fails, escalate to another who can help. "
        "Never just report the failure — always attempt a fix or workaround",
        "7. **Tool requests**: When a member returns a message starting with "
        "'TOOL_REQUEST:', act based on the status field:",
        "   - **enabled_not_assigned** → call "
        "assign_tool_to_member(tool_name, member_name) immediately, "
        "then re-delegate the original task",
        "   - **not_enabled** → ask the user: 'Member X needs {tool_name} "
        "to {reason}. Should I enable it?' If yes, call enable_tool() "
        "then assign_tool_to_member(), then re-delegate",
        "   - **not_found** → tell the user the tool doesn't exist in the "
        "catalog. Suggest creating a custom one with "
        "`vandelay tools create <name>` or delegate to the Vandelay Expert "
        "to build it",
        "",
        "## When to Delegate to Vandelay Expert",
        "Delegate to the Vandelay Expert whenever the user:",
        "- Asks to create, modify, or improve an agent or team member",
        "- Asks about which tools to enable or assign to an agent",
        "- Wants to understand how Vandelay or Agno works",
        "- Reports that an agent isn't performing well or behaving as expected",
        "- Asks about prompt engineering, agent design, or best practices",
        "- Wants to add a new specialist to the team",
        "- Asks questions like 'how do I make X better?' about any agent",
        "The Vandelay Expert is the authority on agent creation and platform capabilities. "
        "Do NOT try to handle these yourself — delegate.",
    ])

    return "\n".join(lines)


def _build_deep_work_prompt(settings: Settings) -> str:
    """Generate a deep work section for the team leader prompt.

    Only included when deep_work.enabled is True.
    """
    cfg = settings.deep_work
    if not cfg.enabled:
        return ""

    activation_desc = {
        "suggest": (
            "When you detect a complex request that would benefit from extended "
            "autonomous work (multi-step research, large implementations, etc.), "
            "suggest using deep work to the user. Wait for their confirmation."
        ),
        "explicit": (
            "Only use deep work when the user explicitly asks for it. "
            "Do not suggest it proactively."
        ),
        "auto": (
            "Automatically start deep work for complex requests without asking. "
            "Use your judgment to determine when a task warrants deep work."
        ),
    }

    lines = [
        "# Deep Work",
        "",
        "You have access to **deep work** — autonomous background execution for "
        "complex, multi-step tasks. When activated, a separate team runs in the "
        "background, breaking down the objective into tasks, delegating to "
        "specialists, and iterating until done.",
        "",
        "## When to Use",
        activation_desc.get(cfg.activation, activation_desc["suggest"]),
        "",
        "Good candidates for deep work:",
        "- Research projects requiring multiple searches and synthesis",
        "- Multi-step implementations across several files",
        "- Tasks that would take many tool calls and iterations",
        "- Overnight or long-running work",
        "",
        "## Tools",
        "- `start_deep_work(objective)` — Launch a background session",
        "- `check_deep_work_status()` — Check progress of active session",
        "- `cancel_deep_work()` — Stop the active session",
        "",
        "## Safeguards",
        f"- Max iterations: {cfg.max_iterations}",
        f"- Time limit: {cfg.max_time_minutes} minutes",
        f"- Progress updates every {cfg.progress_interval_minutes} minutes",
        "- User can cancel at any time",
        "",
        "Normal chat continues uninterrupted while deep work runs in the background.",
    ]

    return "\n".join(lines)


def build_team_leader_prompt(
    agent_name: str = "Art",
    workspace_dir: Path | None = None,
    settings: Settings | None = None,
) -> str:
    """Assemble a slim system prompt for the team leader.

    Compared to ``build_system_prompt()``, this:
    - Skips TOOLS.md and the tool catalog (members handle tool execution)
    - Uses a slim AGENTS.md (workspace, safety, style only — no delegation)
    - Adds a dynamic member roster generated from config
    """
    sections: list[str] = []

    # Agent identity preamble + current date/time so the agent never
    # falls back to its training-cutoff date for scheduling tasks.
    from datetime import datetime

    now = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    sections.append(f"Your name is **{agent_name}**.\n\nCurrent date and time: {now}")

    soul = get_template_content("SOUL.md", workspace_dir)
    if soul:
        sections.append(soul)

    user = get_template_content("USER.md", workspace_dir)
    if user:
        sections.append(user)

    agents_slim = _build_agents_slim(workspace_dir)
    if agents_slim:
        sections.append(agents_slim)

    # Dynamic member roster (instead of TOOLS.md + catalog)
    if settings is not None:
        roster = _build_member_roster(settings)
        if roster:
            sections.append(roster)

        deep_work_prompt = _build_deep_work_prompt(settings)
        if deep_work_prompt:
            sections.append(deep_work_prompt)

    # Dynamic credentials summary
    creds = _build_credentials_summary()
    if creds:
        sections.append(creds)

    heartbeat = get_template_content("HEARTBEAT.md", workspace_dir)
    if heartbeat:
        sections.append(heartbeat)

    # Bootstrap — same logic as standalone prompt (read once, auto-delete)
    if workspace_dir:
        bootstrap_path = workspace_dir / "BOOTSTRAP.md"
        if bootstrap_path.exists():
            sections.append(bootstrap_path.read_text(encoding="utf-8"))
            with contextlib.suppress(OSError):
                bootstrap_path.unlink()

    return "\n\n---\n\n".join(sections)
