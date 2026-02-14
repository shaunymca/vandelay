"""Starter agent templates — predefined personas for the CLI member picker."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path


@dataclass(frozen=True)
class StarterTemplate:
    """Metadata for a starter agent template."""

    slug: str
    name: str
    role: str
    suggested_tools: list[str] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return f"{self.slug}.md"


STARTER_TEMPLATES: dict[str, StarterTemplate] = {
    t.slug: t
    for t in [
        StarterTemplate(
            slug="cto",
            name="CTO",
            role="Hands-on technical leader — architecture, code review, engineering decisions, and system design",
            suggested_tools=["shell", "file", "python", "github", "camofox"],
        ),
        StarterTemplate(
            slug="sales-exec",
            name="Sales Executive",
            role="B2B outbound prospecting, pipeline building, cold outreach, and deal qualification",
            suggested_tools=["gmail", "googlesheets", "tavily", "camofox"],
        ),
        StarterTemplate(
            slug="marketer",
            name="Marketer",
            role="Growth marketing for SaaS — social, content, email lists, campaigns, and analytics",
            suggested_tools=["gmail", "tavily", "googlesheets", "camofox"],
        ),
        StarterTemplate(
            slug="personal-assistant",
            name="Personal Assistant",
            role="Proactive life admin — scheduling, reminders, email triage, travel, and errands",
            suggested_tools=["googlecalendar", "gmail", "tavily", "google_maps", "camofox"],
        ),
        StarterTemplate(
            slug="chef",
            name="Chef",
            role="Ingredient-driven cooking — recipes, meal planning, dietary guidance, and grocery lists",
            suggested_tools=["tavily", "googlesheets", "camofox"],
        ),
        StarterTemplate(
            slug="personal-trainer",
            name="Personal Trainer",
            role="Full fitness programs with check-ins, form guidance, nutrition, and progress tracking",
            suggested_tools=["tavily", "googlesheets", "camofox"],
        ),
        StarterTemplate(
            slug="ai-engineer",
            name="AI Engineer",
            role="Prompt engineering, model selection, fine-tuning, evaluation, and AI tool recommendations",
            suggested_tools=["tavily", "crawl4ai", "python", "file", "camofox"],
        ),
        StarterTemplate(
            slug="research-analyst",
            name="Research Analyst",
            role="Deep research with formal deliverables — reports, competitive intel, and data synthesis",
            suggested_tools=["tavily", "crawl4ai", "wikipedia", "google_drive", "notion", "camofox"],
        ),
        StarterTemplate(
            slug="vandelay-expert",
            name="Vandelay Expert",
            role="Agent builder — designs, creates, tests, and improves team member agents",
            suggested_tools=["file", "python", "shell", "camofox"],
        ),
        StarterTemplate(
            slug="writer",
            name="Writer",
            role="Self-editing generalist writer — polished drafts, natural voice, multiple formats",
            suggested_tools=["tavily", "file", "google_drive", "notion", "camofox"],
        ),
        StarterTemplate(
            slug="data-analyst",
            name="Data Analyst",
            role="Data exploration, written analysis, Python/pandas, SQL, and actionable insights",
            suggested_tools=["python", "file", "duckdb", "googlesheets", "csv_toolkit", "camofox"],
        ),
        StarterTemplate(
            slug="devops",
            name="DevOps / SysAdmin",
            role="Cloud-first infrastructure, CI/CD, automation, security hardening, and monitoring",
            suggested_tools=["shell", "file", "docker", "github", "python", "camofox"],
        ),
        StarterTemplate(
            slug="content-creator",
            name="Content Creator",
            role="Social media, video scripts with editing notes, newsletters, and audience growth",
            suggested_tools=["tavily", "dalle", "camofox", "x"],
        ),
        StarterTemplate(
            slug="project-manager",
            name="Project Manager",
            role="Technical PM — owns roadmap, assigns tasks, tracks progress, coordinates across agents",
            suggested_tools=["notion", "googlesheets", "linear", "jira", "gmail", "camofox"],
        ),
    ]
}


def get_template_content(slug: str) -> str:
    """Read the markdown content of a starter template.

    Returns the template text or raises FileNotFoundError.
    """
    pkg = resources.files("vandelay.agents.templates")
    resource = pkg.joinpath(f"{slug}.md")
    return resource.read_text(encoding="utf-8")


def list_templates() -> list[StarterTemplate]:
    """Return all starter templates sorted by name."""
    return sorted(STARTER_TEMPLATES.values(), key=lambda t: t.name)
