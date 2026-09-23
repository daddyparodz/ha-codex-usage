"""Tests for automatic Codex device login."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.codex_usage import config_flow
from custom_components.codex_usage.auth_device import DeviceLoginExpired
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


class FakeHass:
    """Minimal Home Assistant task API used by the progress flow."""

    def async_create_task(self, coro):
        return asyncio.create_task(coro)


def _flow() -> CodexUsageConfigFlow:
    flow = CodexUsageConfigFlow()
    flow.hass = FakeHass()
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


def test_device_code_copy_step_is_copyable() -> None:
    """Show the device code in an editable text field before login progress."""
    flow = _flow()

    result = asyncio.run(flow.async_step_device_code_copy())

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_code_copy"
    assert result["last_step"] is False
    assert result["data_schema"]({})["user_code"] == "ABCDEFGH"

    selector_value = next(iter(result["data_schema"].schema.values()))
    assert isinstance(selector_value, config_flow.selector.TextSelector)
    assert selector_value.config.get("read_only") is not True


@pytest.mark.asyncio
async def test_device_code_copy_step_starts_progress(monkeypatch) -> None:
    """Start automatic polling after the user has copied the code."""
    gate = asyncio.Event()

    async def wait_for_login(*args, **kwargs):
        await gate.wait()
        return {
            "authorization_code": "authorization-code",
            "code_verifier": "code-verifier",
        }

    flow = _flow()
    monkeypatch.setattr(config_flow, "wait_for_device_login", wait_for_login)

    result = await flow.async_step_device_code_copy({"user_code": "ABCDEFGH"})

    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert flow._device_login_task is not None
    flow.async_remove()
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_device_login_pending(monkeypatch) -> None:
    """Keep the progress step open while Codex authorization is pending."""
    gate = asyncio.Event()

    async def wait_for_login(*args, **kwargs):
        await gate.wait()
        return {
            "authorization_code": "authorization-code",
            "code_verifier": "code-verifier",
        }

    flow = _flow()
    monkeypatch.setattr(config_flow, "wait_for_device_login", wait_for_login)

    result = await flow.async_step_device_code()

    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "wait_for_device"
    assert result["description_placeholders"] == {
        "verification_url": "https://example.test/codex/device",
    }
    assert flow._device_login_task is not None
    flow.async_remove()
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_device_login_completed_creates_entry(monkeypatch) -> None:
    """Advance automatically and create the same config entry data as before."""
    flow = _flow()
    monkeypatch.setattr(
        config_flow,
        "wait_for_device_login",
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
        AsyncMock(
            return_value={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "id_token": "id-token",
                "account_id": "account-id",
            }
        ),
    )

    progress = await flow.async_step_device_code()
    await progress["progress_task"]
    done = await flow.async_step_device_code()
    result = await flow.async_step_device_code_done()

    assert done["type"] is FlowResultType.SHOW_PROGRESS_DONE
    assert done["step_id"] == "device_code_done"
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_AUTH_METHOD] == AUTH_METHOD_DEVICE
    assert result["data"][CONF_ACCESS_TOKEN] == "access-token"
    assert result["data"][CONF_REFRESH_TOKEN] == "refresh-token"
    assert result["data"][CONF_ID_TOKEN] == "id-token"
    assert result["data"][CONF_ACCOUNT_ID] == "account-id"


@pytest.mark.asyncio
async def test_device_login_failed_allows_retry(monkeypatch) -> None:
    """Surface a polling failure and allow generating a fresh device code."""
    flow = _flow()
    monkeypatch.setattr(
        config_flow,
        "wait_for_device_login",
        AsyncMock(side_effect=RuntimeError("poll failed")),
    )

    progress = await flow.async_step_device_code()
    with pytest.raises(RuntimeError):
        await progress["progress_task"]
    done = await flow.async_step_device_code()
    retry = await flow.async_step_device_code_retry()

    assert done["type"] is FlowResultType.SHOW_PROGRESS_DONE
    assert done["step_id"] == "device_code_retry"
    assert retry["type"] is FlowResultType.FORM
    assert retry["errors"] == {"base": "device_code_poll_failed"}


@pytest.mark.asyncio
async def test_device_code_expired_allows_retry(monkeypatch) -> None:
    """Surface device-code expiry separately from other auth failures."""
    flow = _flow()
    monkeypatch.setattr(
        config_flow,
        "wait_for_device_login",
        AsyncMock(side_effect=DeviceLoginExpired("expired")),
    )

    progress = await flow.async_step_device_code()
    with pytest.raises(DeviceLoginExpired):
        await progress["progress_task"]
    done = await flow.async_step_device_code()
    retry = await flow.async_step_device_code_retry()

    assert done["step_id"] == "device_code_retry"
    assert retry["errors"] == {"base": "device_code_expired"}


@pytest.mark.asyncio
async def test_token_exchange_failure_allows_retry(monkeypatch) -> None:
    """Keep token exchange errors distinct after device authorization succeeds."""
    flow = _flow()
    monkeypatch.setattr(
        config_flow,
        "wait_for_device_login",
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

    progress = await flow.async_step_device_code()
    with pytest.raises(config_flow.DeviceTokenExchangeError):
        await progress["progress_task"]
    await flow.async_step_device_code()
    retry = await flow.async_step_device_code_retry()

    assert retry["errors"] == {"base": "token_exchange_failed"}


@pytest.mark.asyncio
async def test_device_login_task_cancelled_on_flow_remove(monkeypatch) -> None:
    """Do not leave a polling task behind when the config flow is abandoned."""
    started = asyncio.Event()

    async def wait_forever(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    flow = _flow()
    monkeypatch.setattr(config_flow, "wait_for_device_login", wait_forever)

    await flow.async_step_device_code()
    task = flow._device_login_task
    assert task is not None
    await started.wait()

    flow.async_remove()
    await asyncio.sleep(0)

    assert task.cancelled()
    assert flow._device_login_task is None


@pytest.mark.asyncio
async def test_device_login_step_reuses_same_task(monkeypatch) -> None:
    """Do not start duplicate polling when Home Assistant revisits the progress step."""
    gate = asyncio.Event()
    wait = Mock()

    async def wait_for_login(*args, **kwargs):
        wait()
        await gate.wait()
        return {
            "authorization_code": "authorization-code",
            "code_verifier": "code-verifier",
        }

    flow = _flow()
    monkeypatch.setattr(config_flow, "wait_for_device_login", wait_for_login)

    first = await flow.async_step_device_code()
    first_task = flow._device_login_task
    second = await flow.async_step_device_code()

    assert first["progress_task"] is first_task
    assert second["progress_task"] is first_task
    await asyncio.sleep(0)
    assert wait.call_count == 1

    flow.async_remove()
    await asyncio.sleep(0)


def test_device_login_progress_copy_uses_real_newlines() -> None:
    """Keep progress copy readable in Home Assistant markdown."""
    for path in (
        Path("custom_components/codex_usage/strings.json"),
        Path("custom_components/codex_usage/translations/it.json"),
    ):
        data = json.loads(path.read_text())
        message = data["config"]["progress"]["wait_for_device"]

        assert "\n" in message
        assert "\\n" not in message
        assert "{verification_url}" in message
        assert "{user_code}" not in message
