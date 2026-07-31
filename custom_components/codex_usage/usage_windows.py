"""Helpers for identifying Codex usage windows."""

from __future__ import annotations

from time import time

WEEKLY_WINDOW_MIN_SECONDS = 24 * 60 * 60


def _window_duration(window: dict) -> int | None:
    value = window.get("limit_window_seconds") or window.get("limitWindowSeconds")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def classify_rate_limit_windows(rate: dict) -> tuple[dict, dict]:
    """Return the short and weekly windows regardless of API field position."""
    primary = rate.get("primary_window") or rate.get("primary") or {}
    secondary = rate.get("secondary_window") or rate.get("secondary") or {}
    windows = [window for window in (primary, secondary) if isinstance(window, dict) and window]

    if not windows:
        return {}, {}

    if len(windows) == 1:
        only = windows[0]
        duration = _window_duration(only)
        return ({}, only) if duration and duration >= WEEKLY_WINDOW_MIN_SECONDS else (only, {})

    first_duration = _window_duration(windows[0])
    second_duration = _window_duration(windows[1])
    if first_duration is not None and second_duration is not None:
        return tuple(sorted(windows, key=_window_duration))

    # Preserve the API's traditional primary/secondary meaning if duration
    # metadata is unavailable.
    return windows[0], windows[1]


def window_used_percent(window: dict) -> float | None:
    """Return a window's used percentage without inventing a missing value."""
    value = window.get("used_percent")
    if value is None:
        value = window.get("usedPercent")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def window_reset_epoch(window: dict, now_epoch: float | None = None) -> int | None:
    """Return the absolute reset epoch, deriving it from a relative value if needed."""
    reset_at = window.get("reset_at")
    if reset_at is None:
        reset_at = window.get("resetAt")
    try:
        if reset_at is not None:
            return int(reset_at)
    except (TypeError, ValueError):
        return None

    reset_after = window.get("reset_after_seconds")
    if reset_after is None:
        reset_after = window.get("resetAfterSeconds")
    try:
        if reset_after is not None:
            return int((now_epoch if now_epoch is not None else time()) + float(reset_after))
    except (TypeError, ValueError):
        return None
    return None
