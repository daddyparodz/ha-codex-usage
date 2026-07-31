"""Tests for reset-credit response normalization."""

import unittest
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "codex_usage"
    / "reset_credits.py"
)
SPEC = spec_from_file_location("codex_usage_reset_credits", MODULE_PATH)
assert SPEC and SPEC.loader
RESET_CREDITS = module_from_spec(SPEC)
SPEC.loader.exec_module(RESET_CREDITS)


class NormalizeResetCreditsTest(unittest.TestCase):
    def test_normalizes_active_expired_and_unknown_credits(self):
        payload = {
            "available_count": 2,
            "credits": [
                {
                    "granted_at": "2026-07-01T20:25:51Z",
                    "expires_at": "2026-07-31T20:25:51Z",
                },
                {
                    "granted_at": "2026-07-13T18:05:12Z",
                    "expires_at": "2026-08-12T18:05:12Z",
                },
                {"granted_at": "invalid", "expires_at": "invalid"},
            ],
        }

        result = RESET_CREDITS.normalize_reset_credits(
            payload, datetime(2026, 7, 31, 19, 0, tzinfo=UTC)
        )

        self.assertEqual(result["reset_credits_available"], 2)
        self.assertEqual(result["reset_credits"][0]["id"], "9cc86a233ec2")
        self.assertEqual(result["reset_credits"][0]["status"], "active")
        self.assertEqual(result["reset_credits"][0]["remaining"], "1h 25m")
        self.assertEqual(result["reset_credits"][1]["remaining"], "11d 23h 5m")
        self.assertEqual(result["reset_credits"][2]["status"], "unknown")
        self.assertEqual(
            result["reset_credits_next_expiration"], "2026-07-31T20:25:51+00:00"
        )

    def test_derives_count_when_api_omits_available_count(self):
        payload = {
            "credits": [
                {"expires_at": "2026-08-01T00:00:00Z"},
                {"expires_at": "2026-07-01T00:00:00Z"},
            ]
        }

        result = RESET_CREDITS.normalize_reset_credits(
            payload, datetime(2026, 7, 31, 19, 0, tzinfo=UTC)
        )

        self.assertEqual(result["reset_credits_available"], 1)
        self.assertEqual(result["reset_credits"][1]["status"], "expired")

    def test_credit_identity_is_stable_and_unique(self):
        payload = {
            "credits": [
                {
                    "granted_at": "2026-07-01T20:25:51Z",
                    "expires_at": "2026-07-31T20:25:51Z",
                },
                {
                    "granted_at": "2026-07-13T18:05:12Z",
                    "expires_at": "2026-08-12T18:05:12Z",
                },
            ]
        }

        first = RESET_CREDITS.normalize_reset_credits(payload)
        second = RESET_CREDITS.normalize_reset_credits(payload)

        self.assertEqual(first["reset_credits"][0]["id"], second["reset_credits"][0]["id"])
        self.assertNotEqual(first["reset_credits"][0]["id"], first["reset_credits"][1]["id"])

    def test_rejects_invalid_credits_collection(self):
        with self.assertRaisesRegex(ValueError, "unexpected credits"):
            RESET_CREDITS.normalize_reset_credits({"credits": {}})


if __name__ == "__main__":
    unittest.main()
