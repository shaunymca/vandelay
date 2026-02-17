"""Integration tests for Google Drive via Agno's GoogleDriveTools."""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestGoogleDrive:
    def test_list_files(self, drive_tool):
        """List files from Drive — verifies auth and basic API access."""
        result = drive_tool.list_files(page_size=5)
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"
