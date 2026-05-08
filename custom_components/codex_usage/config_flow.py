"""Config flow for Codex Usage integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .auth_device import exchange_code_for_tokens, poll_device_code_once, request_device_code
from .const import (
    AUTH_METHOD_AUTH_JSON,
    AUTH_METHOD_DEVICE,
    AUTH_METHOD_TOKEN,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_AUTH_METHOD,
    CONF_BACKEND_URL,
    CONF_CODEX_HOME,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_BACKEND_URL,
    DEFAULT_CODEX_HOME,
    DEFAULT_REFRESH_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class CodexUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Codex Usage."""

    VERSION = 1

    def __init__(self) -> None:
        self._auth_method = AUTH_METHOD_DEVICE
        self._base_config: dict = {
            CONF_CODEX_HOME: DEFAULT_CODEX_HOME,
            CONF_BACKEND_URL: DEFAULT_BACKEND_URL,
            CONF_REFRESH_URL: DEFAULT_REFRESH_URL,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_ACCOUNT_ID: "",
        }
        self._device_state: dict = {}

    async def async_step_user(self, user_input=None):
        """Choose auth method first (clean UX)."""
        await self.async_set_unique_id("codex_usage_singleton")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._auth_method = user_input[CONF_AUTH_METHOD]
            if self._auth_method == AUTH_METHOD_DEVICE:
                try:
                    self._device_state = await request_device_code(self.hass)
                except RuntimeError:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=_method_schema(),
                        errors={"base": "device_code_init_failed"},
                    )
                return await self.async_step_device_code()

            if self._auth_method == AUTH_METHOD_AUTH_JSON:
                return await self.async_step_auth_json()

            return await self.async_step_access_token()

        return self.async_show_form(step_id="user", data_schema=_method_schema())

    async def async_step_device_code(self, user_input=None):
        errors = {}

        if user_input is not None:
            if not user_input.get("confirm_done"):
                errors["base"] = "device_code_not_completed"
            else:
                try:
                    polled = await poll_device_code_once(
                        self.hass,
                        self._device_state["device_auth_id"],
                        self._device_state["user_code"],
                    )
                except RuntimeError:
                    errors["base"] = "device_code_poll_failed"
                else:
                    if polled is None:
                        errors["base"] = "device_code_pending"
                    else:
                        try:
                            tokens = await exchange_code_for_tokens(
                                self.hass,
                                polled["authorization_code"],
                                polled["code_verifier"],
                            )
                        except RuntimeError:
                            errors["base"] = "token_exchange_failed"
                        else:
                            self._base_config.update(
                                {
                                    CONF_ACCESS_TOKEN: tokens["access_token"],
                                    CONF_REFRESH_TOKEN: tokens["refresh_token"],
                                    CONF_ID_TOKEN: tokens["id_token"],
                                    CONF_ACCOUNT_ID: tokens.get("account_id") or "",
                                    CONF_AUTH_METHOD: AUTH_METHOD_DEVICE,
                                }
                            )
                            return await self.async_step_advanced()

        schema = vol.Schema({vol.Required("confirm_done", default=False): bool})
        return self.async_show_form(
            step_id="device_code",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "verification_url": self._device_state.get("verification_url", ""),
                "user_code": self._device_state.get("user_code", ""),
            },
        )

    async def async_step_auth_json(self, user_input=None):
        if user_input is not None:
            self._base_config.update(
                {
                    CONF_AUTH_METHOD: AUTH_METHOD_AUTH_JSON,
                    CONF_CODEX_HOME: user_input[CONF_CODEX_HOME],
                    CONF_ACCESS_TOKEN: "",
                    CONF_REFRESH_TOKEN: "",
                    CONF_ID_TOKEN: "",
                }
            )
            return await self.async_step_advanced()

        schema = vol.Schema(
            {
                vol.Optional(CONF_CODEX_HOME, default=self._base_config[CONF_CODEX_HOME]): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="auth_json", data_schema=schema)

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
                return await self.async_step_advanced()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_ACCOUNT_ID, default=self._base_config.get(CONF_ACCOUNT_ID, "")): selector.TextSelector(),
            }
        )
        return self.async_show_form(
            step_id="access_token", data_schema=schema, errors=errors
        )

    async def async_step_advanced(self, user_input=None):
        if user_input is not None:
            self._base_config.update(
                {
                    CONF_BACKEND_URL: user_input[CONF_BACKEND_URL],
                    CONF_REFRESH_URL: user_input[CONF_REFRESH_URL],
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }
            )
            return self.async_create_entry(title="Codex Usage", data=self._base_config)

        schema = vol.Schema(
            {
                vol.Optional(CONF_BACKEND_URL, default=self._base_config[CONF_BACKEND_URL]): selector.TextSelector(),
                vol.Optional(CONF_REFRESH_URL, default=self._base_config[CONF_REFRESH_URL]): selector.TextSelector(),
                vol.Optional(CONF_SCAN_INTERVAL, default=self._base_config[CONF_SCAN_INTERVAL]): vol.All(
                    vol.Coerce(int), vol.Range(min=15, max=3600)
                ),
            }
        )
        return self.async_show_form(step_id="advanced", data_schema=schema)


def _method_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_AUTH_METHOD, default=AUTH_METHOD_DEVICE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[AUTH_METHOD_DEVICE, AUTH_METHOD_AUTH_JSON, AUTH_METHOD_TOKEN],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )
