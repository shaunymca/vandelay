"""Integration tests for Google Sheets via Agno's GoogleSheetsTools."""

from __future__ import annotations

import pytest


def _delete_sheet_via_api(creds, sheet_id: str) -> None:
    """Best-effort delete a spreadsheet using the Drive API directly."""
    try:
        from googleapiclient.discovery import build

        service = build("drive", "v3", credentials=creds)
        service.files().delete(fileId=sheet_id).execute()
    except Exception:
        pass


@pytest.mark.integration
class TestGoogleSheets:
    def test_create_write_read_sheet(self, sheets_tool):
        """Create a sheet, write data, read it back, then delete."""
        # 1. Create — returns "Spreadsheet created: https://docs.google.com/spreadsheets/d/ID"
        create_result = sheets_tool.create_sheet("Vandelay Integration Test")
        assert create_result, "create_sheet returned empty result"
        # Extract the spreadsheet ID from the URL
        import re

        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", create_result)
        assert match, f"Could not extract sheet ID from: {create_result}"
        sheet_id = match.group(1)

        try:
            # 2. Write
            data = [["Name", "Value"], ["test", "42"]]
            write_result = sheets_tool.update_sheet(
                data=data,
                spreadsheet_id=sheet_id,
                range_name="Sheet1!A1:B2",
            )
            assert "error" not in write_result.lower(), f"Write failed: {write_result}"

            # 3. Read
            read_result = sheets_tool.read_sheet(
                spreadsheet_id=sheet_id,
                spreadsheet_range="Sheet1!A1:B2",
            )
            assert "42" in read_result, f"Expected '42' in read result: {read_result}"
        finally:
            # 4. Cleanup — use the sheets_tool's creds to delete via Drive API
            _delete_sheet_via_api(sheets_tool.creds, sheet_id)
