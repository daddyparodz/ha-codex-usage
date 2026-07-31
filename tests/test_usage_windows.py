"""Tests for Codex usage-window classification."""

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "codex_usage"
    / "usage_windows.py"
)
SPEC = spec_from_file_location("codex_usage_windows", MODULE_PATH)
assert SPEC and SPEC.loader
WINDOWS = module_from_spec(SPEC)
SPEC.loader.exec_module(WINDOWS)


class UsageWindowsTest(unittest.TestCase):
    def test_keeps_traditional_short_then_weekly_order(self):
        short = {"limit_window_seconds": 18_000, "used_percent": 25}
        weekly = {"limit_window_seconds": 604_800, "used_percent": 50}

        self.assertEqual(
            WINDOWS.classify_rate_limit_windows(
                {"primary_window": short, "secondary_window": weekly}
            ),
            (short, weekly),
        )

    def test_recognizes_weekly_window_in_primary_position(self):
        weekly = {"limit_window_seconds": 604_800, "used_percent": 3}

        self.assertEqual(
            WINDOWS.classify_rate_limit_windows({"primary_window": weekly}),
            ({}, weekly),
        )

    def test_recognizes_single_short_window(self):
        short = {"limit_window_seconds": 18_000, "used_percent": 25}

        self.assertEqual(
            WINDOWS.classify_rate_limit_windows({"primary_window": short}),
            (short, {}),
        )

    def test_orders_reversed_windows_by_duration(self):
        short = {"limit_window_seconds": 18_000}
        weekly = {"limit_window_seconds": 604_800}

        self.assertEqual(
            WINDOWS.classify_rate_limit_windows(
                {"primary_window": weekly, "secondary_window": short}
            ),
            (short, weekly),
        )

    def test_missing_window_values_remain_unknown(self):
        self.assertIsNone(WINDOWS.window_used_percent({}))
        self.assertIsNone(WINDOWS.window_reset_epoch({}))

    def test_derives_reset_epoch_from_relative_seconds(self):
        self.assertEqual(
            WINDOWS.window_reset_epoch({"reset_after_seconds": 120}, now_epoch=1_000),
            1_120,
        )


if __name__ == "__main__":
    unittest.main()
