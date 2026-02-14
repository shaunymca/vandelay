"""Build the system prompt from workspace templates."""

from __future__ import annotations

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
        "These tools are registered and ready to use as direct function calls.",
        "To discover and enable more tools, use `list_available_tools`.",
        "",
    ]

    for entry in sorted(enabled_entries, key=lambda e: (e.category, e.name)):
        desc = entry.description or ""
        if len(desc) > 120:
            desc = desc[:117] + "..."
        suffix = f" — {desc}" if desc else ""
        lines.append(f"- **{entry.name}** [{entry.category}]{suffix}")

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

    # Agent identity preamble
    sections.append(f"Your name is **{agent_name}**.")

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

    memory = get_template_content("MEMORY.md", workspace_dir)
    if memory:
        sections.append(memory)

    # Bootstrap is included only on first run — the agent should
    # delete it from the workspace after the introductory conversation.
    # We check the workspace directly (no fallback to shipped default)
    # because deletion from workspace means it's been used.
    if workspace_dir:
        bootstrap_path = workspace_dir / "BOOTSTRAP.md"
        if bootstrap_path.exists():
            sections.append(bootstrap_path.read_text(encoding="utf-8"))

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

    members = settings.team.members
    if not members:
        return ""

    lines: list[str] = [
        "# Your Team",
        "",
        "Delegate tasks to the best member based on their specialization.",
        "For multi-part requests, delegate to several members and synthesize their results.",
        "For simple questions you can answer directly, just respond — no need to delegate.",
        "",
        "| Member | Role | Tools | Model |",
        "|--------|------|-------|-------|",
    ]

    for entry in members:
        mc = _resolve_member(entry)
        name = mc.name
        role = mc.role or "(no role)"
        tools = ", ".join(mc.tools) if mc.tools else "none"
        if mc.model_provider and mc.model_id:
            model_str = f"{mc.model_provider} / {mc.model_id}"
        else:
            model_str = "inherited"
        lines.append(f"| {name} | {role} | {tools} | {model_str} |")

    lines.extend([
        "",
        "Rules:",
        "- Match tasks to the member whose role fits best",
        "- If no member fits, handle it yourself using your workspace tools",
        "- You can assign new tools to members with assign_tool_to_member()",
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

    # Agent identity preamble
    sections.append(f"Your name is **{agent_name}**.")

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

    memory = get_template_content("MEMORY.md", workspace_dir)
    if memory:
        sections.append(memory)

    # Bootstrap — same logic as standalone prompt
    if workspace_dir:
        bootstrap_path = workspace_dir / "BOOTSTRAP.md"
        if bootstrap_path.exists():
            sections.append(bootstrap_path.read_text(encoding="utf-8"))

    return "\n\n---\n\n".join(sections)
