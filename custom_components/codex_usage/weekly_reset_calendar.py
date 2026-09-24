"""Helpers for representing the weekly Codex reset as a calendar event."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

WEEKLY_RESET_EVENT_DURATION = timedelta(minutes=1)


def build_weekly_reset_event(reset_epoch: int | None) -> dict | None:
    """Build calendar event data for the next weekly usage reset."""
    if reset_epoch is None:
        return None

    try:
        epoch = int(reset_epoch)
        reset_at = datetime.fromtimestamp(epoch, tz=UTC)
    except (OSError, OverflowError, TypeError, ValueError):
        return None

    return {
        "uid": f"codex-weekly-reset-{epoch}",
        "start": reset_at,
        "end": reset_at + WEEKLY_RESET_EVENT_DURATION,
        "summary": "Codex weekly usage reset",
        "description": f"Weekly Codex usage window resets at {reset_at.isoformat()}.",
    }
