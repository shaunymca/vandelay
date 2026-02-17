"""Integration tests for Gmail via Agno's GmailTools."""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestGmail:
    def test_create_draft(self, gmail_tool):
        """Create a draft email (not sent) and verify success."""
        result = gmail_tool.create_draft_email(
            to="integration-test@example.com",
            subject="Vandelay Integration Test Draft",
            body="This draft was auto-created by an integration test.",
        )
        assert "error" not in result.lower(), f"create_draft_email failed: {result}"

    def test_search_emails(self, gmail_tool):
        """Search for emails — verifies auth and basic API functionality."""
        result = gmail_tool.search_emails(query="test", count=3)
        assert result is not None, "search_emails returned None"
        # Don't check for "error" substring — email bodies may contain that word.
        # A real API error raises an exception or returns None.
        assert isinstance(result, str) and len(result) > 0, (
            f"search_emails returned unexpected result: {result}"
        )

    def test_get_latest(self, gmail_tool):
        """Fetch the latest email — verifies inbox read access."""
        result = gmail_tool.get_latest_emails(count=1)
        assert result is not None, "get_latest_emails returned None"
        assert "error" not in str(result).lower(), (
            f"get_latest_emails failed: {result}"
        )
