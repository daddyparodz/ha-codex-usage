"""Normalization helpers for Codex rate-limit reset credits."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _format_remaining(seconds: int) -> str:
    minutes = seconds // 60
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def normalize_reset_credits(payload: object, now: datetime | None = None) -> dict:
    """Convert the reset-credit API response into stable HA state and attributes."""
    if not isinstance(payload, dict):
        raise ValueError("The reset-credit API returned an unexpected response")

    raw_credits = payload.get("credits")
    if raw_credits is None:
        raw_credits = []
    if not isinstance(raw_credits, list):
        raise ValueError("The reset-credit API returned an unexpected credits value")

    current = now or datetime.now(tz=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    credits: list[dict] = []
    active_expirations: list[datetime] = []
    for raw_credit in raw_credits:
        if not isinstance(raw_credit, dict):
            continue

        granted_at = raw_credit.get("granted_at")
        expires_at = raw_credit.get("expires_at")
        expiry = parse_timestamp(expires_at)
        source_id = raw_credit.get("id")
        identity = source_id or f"{granted_at or ''}|{expires_at or ''}"
        credit = {
            "id": hashlib.sha256(identity.encode()).hexdigest()[:12],
            "granted_at": granted_at if isinstance(granted_at, str) else None,
            "expires_at": expires_at if isinstance(expires_at, str) else None,
            "redeemed_at": raw_credit.get("redeemed_at"),
        }

        api_status = raw_credit.get("status")
        if isinstance(api_status, str) and api_status:
            credit["status"] = api_status.lower()
        elif expiry is None:
            credit["status"] = "unknown"
        elif expiry <= current:
            credit["status"] = "expired"
        else:
            credit["status"] = "active"

        if expiry is None:
            credit["remaining"] = None
        else:
            remaining_seconds = max(0, int((expiry - current).total_seconds()))
            credit["remaining"] = _format_remaining(remaining_seconds)
            if credit["status"] in ("active", "available") and remaining_seconds:
                active_expirations.append(expiry)

        credits.append(credit)

    available_count = payload.get("available_count")
    if not isinstance(available_count, int) or isinstance(available_count, bool):
        available_count = sum(
            credit["status"] in ("active", "available") for credit in credits
        )

    next_expiration = min(active_expirations).isoformat() if active_expirations else None
    return {
        "reset_credits_available": available_count,
        "reset_credits": credits,
        "reset_credits_next_expiration": next_expiration,
    }
