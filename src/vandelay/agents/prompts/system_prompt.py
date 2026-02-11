"""Build the system prompt from workspace templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from vandelay.workspace.manager import get_template_content

if TYPE_CHECKING:
    from vandelay.config.settings import Settings


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
    lines: list[str] = [
        "# Available Tool Catalog",
        "",
        "You can enable or disable any of these tools using your "
        "tool management functions (`enable_tool`, `disable_tool`, "
        "`list_available_tools`, `get_tool_info`).",
        "",
    ]

    for category in sorted(by_cat):
        lines.append(f"## {category.title()}")
        for entry in sorted(by_cat[category], key=lambda e: e.name):
            status = "ENABLED" if entry.name in enabled else "available"
            desc = entry.description or ""
            # Truncate to keep prompt lean
            if len(desc) > 100:
                desc = desc[:97] + "..."
            suffix = f" — {desc}" if desc else ""
            lines.append(f"- {entry.name} [{status}]{suffix}")
        lines.append("")

    return "\n".join(lines)


def build_system_prompt(
    agent_name: str = "Claw",
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
