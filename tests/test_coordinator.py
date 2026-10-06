"""Tests for Codex Usage coordinator authentication handling."""

from custom_components.codex_usage.coordinator import _refresh_requires_reauth


def test_invalid_refresh_credentials_require_reauth() -> None:
    """Treat revoked or invalid refresh credentials as permanent auth failures."""
    assert _refresh_requires_reauth(401, "{}")
    assert _refresh_requires_reauth(403, "{}")
    assert _refresh_requires_reauth(
        400, '{"error":{"code":"refresh_token_invalidated"}}'
    )
    assert _refresh_requires_reauth(400, '{"error":"invalid_grant"}')


def test_transient_refresh_failures_do_not_require_reauth() -> None:
    """Keep retryable refresh failures on the normal coordinator retry path."""
    assert not _refresh_requires_reauth(400, '{"error":"temporarily_unavailable"}')
    assert not _refresh_requires_reauth(429, "rate limited")
    assert not _refresh_requires_reauth(500, "server error")
