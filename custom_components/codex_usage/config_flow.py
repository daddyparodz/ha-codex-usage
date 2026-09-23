"""Config flow for Codex Usage integration."""

from __future__ import annotations

import asyncio

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .auth_device import (
    DeviceLoginExpired,
    exchange_code_for_tokens,
    request_device_code,
    wait_for_device_login,
)
from .const import (
    AUTH_METHOD_DEVICE,
    AUTH_METHOD_TOKEN,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_AUTH_METHOD,
    CONF_BACKEND_URL,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_BACKEND_URL,
    DEFAULT_REFRESH_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class DeviceTokenExchangeError(RuntimeError):
    """Error raised when Codex accepts the device login but token exchange fails."""


class CodexUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Codex Usage."""

    VERSION = 1

    def __init__(self) -> None:
        self._auth_method = AUTH_METHOD_DEVICE
        self._base_config: dict = {
            CONF_BACKEND_URL: DEFAULT_BACKEND_URL,
            CONF_REFRESH_URL: DEFAULT_REFRESH_URL,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_ACCOUNT_ID: "",
        }
        self._device_state: dict = {}
        self._device_login_task: asyncio.Task[dict] | None = None
        self._device_login_tokens: dict | None = None
        self._device_login_error: str | None = None

    @staticmethod
    def async_get_options_flow(config_entry):
        return CodexUsageOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Choose auth method first."""
        await self.async_set_unique_id("codex_usage_singleton")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._auth_method = user_input[CONF_AUTH_METHOD]
            self._base_config[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

            if self._auth_method == AUTH_METHOD_DEVICE:
                self._reset_device_login_state()
                try:
                    self._device_state = await request_device_code(self.hass)
                except RuntimeError:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=_method_schema(self._base_config[CONF_SCAN_INTERVAL]),
                        errors={"base": "device_code_init_failed"},
                    )
                return await self.async_step_device_code_copy()

            return await self.async_step_access_token()

        return self.async_show_form(
            step_id="user",
            data_schema=_method_schema(self._base_config[CONF_SCAN_INTERVAL]),
        )

    async def async_step_device_code_copy(self, user_input=None):
        """Show the device code in a copy-friendly field before opening login."""
        if user_input is not None:
            return await self.async_step_device_code()

        schema = vol.Schema(
            {
                vol.Optional(
                    "user_code",
                    default=self._device_state.get("user_code_compact", ""),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(
            step_id="device_code_copy",
            data_schema=schema,
            last_step=False,
        )

    async def _async_complete_device_login(self) -> dict:
        polled = await wait_for_device_login(
            self.hass,
            self._device_state["device_auth_id"],
            self._device_state["user_code"],
            self._device_state["interval"],
        )
        try:
            return await exchange_code_for_tokens(
                self.hass,
                polled["authorization_code"],
                polled["code_verifier"],
            )
        except RuntimeError as err:
            raise DeviceTokenExchangeError from err

    async def async_step_device_code(self, user_input=None):
        """Wait for Codex device login to complete."""
        if (login_task := self._device_login_task) is not None and login_task.done():
            self._device_login_error = None
            try:
                self._device_login_tokens = login_task.result()
            except asyncio.CancelledError:
                self._device_login_error = "device_code_cancelled"
            except DeviceLoginExpired:
                self._device_login_error = "device_code_expired"
            except DeviceTokenExchangeError:
                self._device_login_error = "token_exchange_failed"
            except RuntimeError:
                self._device_login_error = "device_code_poll_failed"
            finally:
                self._device_login_task = None

            return self.async_show_progress_done(
                next_step_id=(
                    "device_code_retry" if self._device_login_error else "device_code_done"
                )
            )

        if self._device_login_task is None:
            self._device_login_task = self.hass.async_create_task(
                self._async_complete_device_login()
            )

        return self.async_show_progress(
            step_id="device_code",
            progress_action="wait_for_device",
            description_placeholders={
                "verification_url": self._device_state.get("verification_url", ""),
            },
            progress_task=self._device_login_task,
        )

    async def async_step_device_code_done(self, user_input=None):
        """Create the config entry after device login completes."""
        tokens = self._device_login_tokens
        if tokens is None:
            self._device_login_error = "device_code_poll_failed"
            return await self.async_step_device_code_retry()

        self._base_config.update(
            {
                CONF_ACCESS_TOKEN: tokens["access_token"],
                CONF_REFRESH_TOKEN: tokens["refresh_token"],
                CONF_ID_TOKEN: tokens["id_token"],
                CONF_ACCOUNT_ID: tokens.get("account_id") or "",
                CONF_AUTH_METHOD: AUTH_METHOD_DEVICE,
            }
        )
        self._device_login_tokens = None
        self._device_state = {}
        return self.async_create_entry(title="Codex Usage", data=self._base_config)

    async def async_step_device_code_retry(self, user_input=None):
        """Allow generating a fresh device code after a failed login."""
        if user_input is not None:
            self._reset_device_login_state()
            try:
                self._device_state = await request_device_code(self.hass)
            except RuntimeError:
                self._device_login_error = "device_code_init_failed"
            else:
                return await self.async_step_device_code_copy()

        return self.async_show_form(
            step_id="device_code_retry",
            errors={"base": self._device_login_error or "device_code_poll_failed"},
        )

    def _reset_device_login_state(self) -> None:
        if self._device_login_task is not None and not self._device_login_task.done():
            self._device_login_task.cancel()
        self._device_login_task = None
        self._device_login_tokens = None
        self._device_login_error = None
        self._device_state = {}

    @callback
    def async_remove(self) -> None:
        """Cancel device login when the config flow is abandoned."""
        self._reset_device_login_state()

    async def async_step_access_token(self, user_input=None):
        errors = {}
        if user_input is not None:
            access_token = (user_input.get(CONF_ACCESS_TOKEN) or "").strip()
            if not access_token:
                errors["base"] = "access_token_required"
            else:
                self._base_config.update(
                    {
                        CONF_AUTH_METHOD: AUTH_METHOD_TOKEN,
                        CONF_ACCESS_TOKEN: access_token,
                        CONF_ACCOUNT_ID: (user_input.get(CONF_ACCOUNT_ID) or "").strip(),
                        CONF_REFRESH_TOKEN: "",
                        CONF_ID_TOKEN: "",
                    }
                )
                return self.async_create_entry(title="Codex Usage", data=self._base_config)

        schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(
                    CONF_ACCOUNT_ID, default=self._base_config.get(CONF_ACCOUNT_ID, "")
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="access_token", data_schema=schema, errors=errors)


class CodexUsageOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Codex Usage."""

    def __init__(self, entry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options.get(
            CONF_SCAN_INTERVAL,
            self._entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=15, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _method_schema(default_scan_interval: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_AUTH_METHOD, default=AUTH_METHOD_DEVICE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[AUTH_METHOD_DEVICE, AUTH_METHOD_TOKEN],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_SCAN_INTERVAL, default=default_scan_interval): vol.All(
                vol.Coerce(int), vol.Range(min=15, max=3600)
            ),
        }
    )
