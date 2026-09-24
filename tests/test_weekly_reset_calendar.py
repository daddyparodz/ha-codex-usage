"""Tests for weekly-reset calendar event generation."""

import sys
import types
import unittest
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "codex_usage"
PACKAGE = types.ModuleType("codex_usage_weekly_calendar_test")
PACKAGE.__path__ = [str(PACKAGE_PATH)]
sys.modules[PACKAGE.__name__] = PACKAGE

spec = spec_from_file_location(
    f"{PACKAGE.__name__}.weekly_reset_calendar",
    PACKAGE_PATH / "weekly_reset_calendar.py",
)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

CALENDAR = module


class WeeklyResetCalendarTest(unittest.TestCase):
    def test_builds_one_minute_event_at_exact_reset_time(self):
        reset_at = datetime(2026, 10, 1, 14, 30, tzinfo=UTC)
        event = CALENDAR.build_weekly_reset_event(int(reset_at.timestamp()))

        self.assertIsNotNone(event)
        self.assertEqual(event["uid"], "codex-weekly-reset-1790865000")
        self.assertEqual(event["start"], reset_at)
        self.assertEqual(
            event["end"],
            datetime(2026, 10, 1, 14, 31, tzinfo=UTC),
        )
        self.assertEqual(event["summary"], "Codex weekly usage reset")

    def test_missing_reset_is_ignored(self):
        self.assertIsNone(CALENDAR.build_weekly_reset_event(None))

    def test_invalid_reset_is_ignored(self):
        self.assertIsNone(CALENDAR.build_weekly_reset_event("invalid"))


if __name__ == "__main__":
    unittest.main()
