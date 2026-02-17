"""Integration tests for Google Calendar via Agno's GoogleCalendarTools."""

from __future__ import annotations

import datetime
import json

import pytest


@pytest.mark.integration
class TestGoogleCalendar:
    def test_create_list_delete_event(self, calendar_tool):
        """Create an event, verify it shows in listing, then delete it."""
        now = datetime.datetime.now(datetime.UTC)
        start = (now + datetime.timedelta(hours=1)).isoformat()
        end = (now + datetime.timedelta(hours=2)).isoformat()

        # 1. Create
        result = calendar_tool.create_event(
            title="Vandelay Integration Test",
            start_date=start,
            end_date=end,
            description="Auto-created by integration test — safe to delete",
        )
        assert "error" not in result.lower(), f"Create failed: {result}"

        # Extract event ID from the JSON response
        event_data = json.loads(result)
        event_id = event_data.get("id") or event_data.get("event_id")
        assert event_id, f"No event ID in response: {result}"

        try:
            # 2. List — verify event appears
            events_raw = calendar_tool.list_events(limit=5)
            assert "Vandelay Integration Test" in events_raw, (
                f"Created event not found in listing: {events_raw}"
            )
        finally:
            # 3. Delete
            delete_result = calendar_tool.delete_event(
                event_id=event_id, notify_attendees=False
            )
            assert "error" not in delete_result.lower(), (
                f"Delete failed: {delete_result}"
            )

    def test_list_calendars(self, calendar_tool):
        """Basic auth check — listing calendars should return data."""
        result = calendar_tool.list_calendars()
        assert result, "list_calendars returned empty"
        assert "error" not in result.lower(), f"list_calendars failed: {result}"
