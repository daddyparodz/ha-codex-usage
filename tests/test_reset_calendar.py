"""Tests for banked-reset calendar event generation."""

import sys
import types
import unittest
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "codex_usage"
PACKAGE = types.ModuleType("codex_usage_test")
PACKAGE.__path__ = [str(PACKAGE_PATH)]
sys.modules[PACKAGE.__name__] = PACKAGE

for name in ("reset_credits", "reset_calendar"):
    spec = spec_from_file_location(
        f"{PACKAGE.__name__}.{name}",
        PACKAGE_PATH / f"{name}.py",
    )
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

CALENDAR = sys.modules[f"{PACKAGE.__name__}.reset_calendar"]


class ResetCalendarTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 31, 19, 0, tzinfo=UTC)
        self.credit = {
            "id": "credit-one",
            "granted_at": "2026-07-13T18:05:12Z",
            "expires_at": "2026-08-12T18:05:12Z",
            "status": "available",
            "remaining": "11d 23h 5m",
            "redeemed_at": None,
        }

    def test_builds_one_event_with_grant_and_expiry(self):
        events = CALENDAR.build_reset_credit_events([self.credit], self.now)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["uid"], "credit-one")
        self.assertEqual(events[0]["start"], datetime(2026, 7, 13, 18, 5, 12, tzinfo=UTC))
        self.assertEqual(events[0]["end"], datetime(2026, 8, 12, 18, 5, 12, tzinfo=UTC))
        self.assertEqual(events[0]["summary"], "Codex banked reset")

    def test_redeemed_credit_disappears(self):
        self.credit["status"] = "redeemed"
        self.credit["redeemed_at"] = "2026-07-31T18:30:00Z"

        self.assertEqual(CALENDAR.build_reset_credit_events([self.credit], self.now), [])

    def test_expired_credit_disappears(self):
        self.credit["expires_at"] = "2026-07-31T18:00:00Z"

        self.assertEqual(CALENDAR.build_reset_credit_events([self.credit], self.now), [])

    def test_invalid_credit_is_ignored(self):
        self.credit["granted_at"] = "invalid"

        self.assertEqual(CALENDAR.build_reset_credit_events([self.credit], self.now), [])

    def test_range_filter_includes_only_overlapping_events(self):
        events = CALENDAR.build_reset_credit_events([self.credit], self.now)

        self.assertEqual(
            CALENDAR.events_in_range(
                events,
                datetime(2026, 8, 1, tzinfo=UTC),
                datetime(2026, 8, 2, tzinfo=UTC),
            ),
            events,
        )
        self.assertEqual(
            CALENDAR.events_in_range(
                events,
                datetime(2026, 9, 1, tzinfo=UTC),
                datetime(2026, 9, 2, tzinfo=UTC),
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
