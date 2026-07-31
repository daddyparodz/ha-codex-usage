"""Pure helpers for representing banked resets as calendar events."""

from __future__ import annotations

from datetime import UTC, datetime

from .reset_credits import parse_timestamp

AVAILABLE_STATUSES = {"active", "available"}


def build_reset_credit_events(
    credits: list[dict], now: datetime | None = None
) -> list[dict]:
    """Build active calendar event data from normalized banked resets."""
    current = now or datetime.now(tz=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    events = []
    for credit in credits:
        status = str(credit.get("status") or "").lower()
        if status not in AVAILABLE_STATUSES or credit.get("redeemed_at"):
            continue

        start = parse_timestamp(credit.get("granted_at"))
        end = parse_timestamp(credit.get("expires_at"))
        if start is None or end is None or end <= start or end <= current:
            continue

        events.append(
            {
                "uid": str(credit.get("id") or ""),
                "start": start,
                "end": end,
                "summary": "Codex banked reset",
                "description": (
                    f"Status: {status}\n"
                    f"Granted: {start.isoformat()}\n"
                    f"Expires: {end.isoformat()}\n"
                    f"Remaining: {credit.get('remaining') or 'unknown'}"
                ),
            }
        )

    return sorted(events, key=lambda event: (event["start"], event["end"]))


def events_in_range(events: list[dict], start: datetime, end: datetime) -> list[dict]:
    """Return events overlapping a requested calendar range."""
    return [event for event in events if event["end"] > start and event["start"] < end]
