"""Tests for starter agent templates."""

from __future__ import annotations

import pytest

from vandelay.agents.templates import (
    STARTER_TEMPLATES,
    StarterTemplate,
    get_template_content,
    list_templates,
)


class TestTemplateRegistry:
    def test_all_13_templates_registered(self):
        assert len(STARTER_TEMPLATES) == 14

    def test_all_slugs_unique(self):
        slugs = list(STARTER_TEMPLATES.keys())
        assert len(slugs) == len(set(slugs))

    def test_all_entries_are_starter_template(self):
        for t in STARTER_TEMPLATES.values():
            assert isinstance(t, StarterTemplate)

    def test_all_have_required_fields(self):
        for slug, t in STARTER_TEMPLATES.items():
            assert t.slug == slug
            assert t.name, f"{slug} missing name"
            assert t.role, f"{slug} missing role"
            assert len(t.suggested_tools) > 0, f"{slug} has no suggested tools"

    def test_all_have_camofox(self):
        for slug, t in STARTER_TEMPLATES.items():
            assert "camofox" in t.suggested_tools, f"{slug} missing camofox"

    def test_filename_property(self):
        t = STARTER_TEMPLATES["cto"]
        assert t.filename == "cto.md"

    def test_ai_exec_renamed_to_ai_engineer(self):
        assert "ai-exec" not in STARTER_TEMPLATES
        assert "ai-engineer" in STARTER_TEMPLATES
        assert STARTER_TEMPLATES["ai-engineer"].name == "AI Engineer"


class TestTemplateContent:
    @pytest.mark.parametrize("slug", list(STARTER_TEMPLATES.keys()))
    def test_template_file_exists_and_readable(self, slug):
        content = get_template_content(slug)
        assert len(content) > 100, f"{slug}.md is too short"

    @pytest.mark.parametrize("slug", list(STARTER_TEMPLATES.keys()))
    def test_template_has_required_sections(self, slug):
        content = get_template_content(slug)
        assert "## Role" in content, f"{slug}.md missing ## Role"
        assert "## Expertise" in content, f"{slug}.md missing ## Expertise"
        assert "## How You Work" in content, f"{slug}.md missing ## How You Work"
        assert "## Boundaries" in content, f"{slug}.md missing ## Boundaries"
        assert "## Tools You Prefer" in content, f"{slug}.md missing ## Tools You Prefer"
        assert "## Memory First" in content, f"{slug}.md missing ## Memory First"

    @pytest.mark.parametrize("slug", list(STARTER_TEMPLATES.keys()))
    def test_template_has_custom_tool_callout(self, slug):
        content = get_template_content(slug)
        assert "custom tool" in content.lower(), (
            f"{slug}.md missing custom tool recommendation callout"
        )

    def test_nonexistent_template_raises(self):
        with pytest.raises(Exception):
            get_template_content("nonexistent-agent")


class TestListTemplates:
    def test_returns_all_templates(self):
        templates = list_templates()
        assert len(templates) == 14

    def test_sorted_by_name(self):
        templates = list_templates()
        names = [t.name for t in templates]
        assert names == sorted(names)

    def test_returns_starter_template_instances(self):
        templates = list_templates()
        for t in templates:
            assert isinstance(t, StarterTemplate)
