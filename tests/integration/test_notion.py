"""Integration tests for Notion via Agno's NotionTools."""

from __future__ import annotations

import json
import uuid

import pytest


@pytest.mark.integration
class TestNotion:
    def test_create_search_update_page(self, notion_tool):
        """Create a page, search by tag, update it, and verify."""
        unique = uuid.uuid4().hex[:8]
        title = f"Vandelay Test {unique}"
        tag = "integration-test"

        # 1. Create
        create_result = notion_tool.create_page(
            title=title,
            tag=tag,
            content=f"Auto-created by integration test run {unique}.",
        )
        assert "error" not in str(create_result).lower(), (
            f"create_page failed: {create_result}"
        )

        # 2. Search by tag
        search_result = notion_tool.search_pages(tag=tag)
        assert unique in str(search_result), (
            f"Created page not found in search results: {search_result}"
        )

        # Extract page ID from search results for update
        # search_pages returns JSON: {"success": true, "pages": [{"page_id": "...", ...}]}
        page_id = None
        try:
            data = json.loads(search_result)
            pages = data.get("pages", []) if isinstance(data, dict) else data
            for page in pages:
                if isinstance(page, dict) and unique in str(page):
                    page_id = page.get("page_id") or page.get("id")
                    break
        except (json.JSONDecodeError, TypeError):
            pass

        assert page_id, (
            f"Could not extract page_id from search results: {search_result}"
        )

        # 3. Update
        update_result = notion_tool.update_page(
            page_id=page_id,
            content=f"Updated by integration test {unique}.",
        )
        assert "error" not in str(update_result).lower(), (
            f"update_page failed: {update_result}"
        )
