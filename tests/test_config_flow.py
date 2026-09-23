"""Tests for the Codex Usage config flow."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from homeassistant.data_entry_flow import FlowResultType

from custom_components.codex_usage import config_flow
from custom_components.codex_usage.config_flow import CodexUsageConfigFlow
from custom_components.codex_usage.const import (
    AUTH_METHOD_DEVICE,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_AUTH_METHOD,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)


def _flow() -> CodexUsageConfigFlow:
    flow = CodexUsageConfigFlow()
    flow.hass = object()
    flow.flow_id = "test-flow"
    flow.handler = DOMAIN
    flow.context = {}
    flow._device_state = {
        "device_auth_id": "device-auth-id",
        "user_code": "ABCD-EFGH",
        "user_code_compact": "ABCDEFGH",
        "verification_url": "https://example.test/codex/device",
        "interval": 5,
    }
    return flow


def test_device_code_confirmation_required(monkeypatch) -> None:
    """Do not poll until the browser-login checkbox is selected."""
    flow = _flow()
    poll = AsyncMock()
    monkeypatch.setattr(config_flow, "poll_device_code_once", poll)

    result = asyncio.run(
        flow.async_step_device_code({"otp_code": "ABCDEFGH", "confirm_done": False})
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_code"
    assert result["errors"] == {"confirm_done": "device_code_not_completed"}
    poll.assert_not_awaited()


def test_device_code_confirmation_proceeds(monkeypatch) -> None:
    """Complete the flow after the user confirms browser login."""
    flow = _flow()
    poll = AsyncMock(
        return_value={
            "authorization_code": "authorization-code",
            "code_verifier": "code-verifier",
        }
    )
    exchange = AsyncMock(
        return_value={
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "id_token": "id-token",
            "account_id": "account-id",
        }
    )
    monkeypatch.setattr(config_flow, "poll_device_code_once", poll)
    monkeypatch.setattr(config_flow, "exchange_code_for_tokens", exchange)

    result = asyncio.run(
        flow.async_step_device_code({"otp_code": "ABCDEFGH", "confirm_done": True})
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_AUTH_METHOD] == AUTH_METHOD_DEVICE
    assert result["data"][CONF_ACCESS_TOKEN] == "access-token"
    assert result["data"][CONF_REFRESH_TOKEN] == "refresh-token"
    assert result["data"][CONF_ID_TOKEN] == "id-token"
    assert result["data"][CONF_ACCOUNT_ID] == "account-id"
    poll.assert_awaited_once()
    exchange.assert_awaited_once_with(flow.hass, "authorization-code", "code-verifier")


def test_device_code_poll_error_is_preserved(monkeypatch) -> None:
    """Keep the existing poll-error handling after confirmation."""
    flow = _flow()
    monkeypatch.setattr(
        config_flow,
        "poll_device_code_once",
        AsyncMock(side_effect=RuntimeError("poll failed")),
    )

    result = asyncio.run(
        flow.async_step_device_code({"otp_code": "ABCDEFGH", "confirm_done": True})
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "device_code_poll_failed"}


def test_token_exchange_error_is_preserved(monkeypatch) -> None:
    """Keep the existing token-exchange error handling after confirmation."""
    flow = _flow()
    monkeypatch.setattr(
        config_flow,
        "poll_device_code_once",
        AsyncMock(
            return_value={
                "authorization_code": "authorization-code",
                "code_verifier": "code-verifier",
            }
        ),
    )
    monkeypatch.setattr(
        config_flow,
        "exchange_code_for_tokens",
        AsyncMock(side_effect=RuntimeError("exchange failed")),
    )

    result = asyncio.run(
        flow.async_step_device_code({"otp_code": "ABCDEFGH", "confirm_done": True})
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "token_exchange_failed"}
