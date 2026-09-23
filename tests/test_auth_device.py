"""Tests for Codex device-code polling helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.codex_usage import auth_device


@pytest.mark.asyncio
async def test_wait_for_device_login_polls_at_server_interval(monkeypatch) -> None:
    """Wait between pending responses instead of busy-looping."""
    poll = AsyncMock(
        side_effect=[
            None,
            {
                "authorization_code": "authorization-code",
                "code_verifier": "code-verifier",
            },
        ]
    )
    sleep = AsyncMock()
    monkeypatch.setattr(auth_device, "poll_device_code_once", poll)
    monkeypatch.setattr(auth_device.asyncio, "sleep", sleep)

    result = await auth_device.wait_for_device_login(
        object(),
        "device-auth-id",
        "ABCD-EFGH",
        7,
        timeout=60,
    )

    assert result["authorization_code"] == "authorization-code"
    assert poll.await_count == 2
    sleep.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_wait_for_device_login_expires(monkeypatch) -> None:
    """Stop polling after the device-code lifetime expires."""
    monkeypatch.setattr(
        auth_device,
        "poll_device_code_once",
        AsyncMock(return_value=None),
    )

    with pytest.raises(auth_device.DeviceLoginExpired):
        await auth_device.wait_for_device_login(
            object(),
            "device-auth-id",
            "ABCD-EFGH",
            5,
            timeout=0,
        )
