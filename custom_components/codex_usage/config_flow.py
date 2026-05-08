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
        self._pending_base_config: dict = {}
        self._device_state: dict = {}

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id("codex_usage_singleton")
            self._abort_if_unique_id_configured()

            auth_method = user_input[CONF_AUTH_METHOD]
            base = {
                CONF_AUTH_METHOD: auth_method,
                CONF_CODEX_HOME: user_input.get(CONF_CODEX_HOME, DEFAULT_CODEX_HOME),
                CONF_BACKEND_URL: user_input.get(CONF_BACKEND_URL, DEFAULT_BACKEND_URL),
                CONF_REFRESH_URL: user_input.get(CONF_REFRESH_URL, DEFAULT_REFRESH_URL),
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                CONF_ACCOUNT_ID: (user_input.get(CONF_ACCOUNT_ID) or "").strip(),
            }

            if auth_method == AUTH_METHOD_DEVICE:
                self._pending_base_config = base
                try:
                    self._device_state = await request_device_code(self.hass)
                except RuntimeError:
                    errors["base"] = "device_code_init_failed"
                else:
                    return await self.async_step_device_code()

            elif auth_method == AUTH_METHOD_TOKEN:
                access_token = (user_input.get(CONF_ACCESS_TOKEN) or "").strip()
                if not access_token:
                    errors["base"] = "access_token_required"
                else:
                    return self.async_create_entry(
                        title="Codex Usage",
                        data={
                            **base,
                            CONF_ACCESS_TOKEN: access_token,
                            CONF_REFRESH_TOKEN: "",
                            CONF_ID_TOKEN: "",
                        },
                    )

            else:
                return self.async_create_entry(
                    title="Codex Usage",
                    data={
                        **base,
                        CONF_ACCESS_TOKEN: "",
                        CONF_REFRESH_TOKEN: "",
                        CONF_ID_TOKEN: "",
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_AUTH_METHOD, default=AUTH_METHOD_DEVICE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[AUTH_METHOD_DEVICE, AUTH_METHOD_AUTH_JSON, AUTH_METHOD_TOKEN],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_CODEX_HOME, default=DEFAULT_CODEX_HOME): selector.TextSelector(),
                vol.Optional(CONF_ACCESS_TOKEN, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_ACCOUNT_ID, default=""): selector.TextSelector(),
                vol.Optional(CONF_BACKEND_URL, default=DEFAULT_BACKEND_URL): selector.TextSelector(),
                vol.Optional(CONF_REFRESH_URL, default=DEFAULT_REFRESH_URL): selector.TextSelector(),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=15, max=3600)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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
                            return self.async_create_entry(
                                title="Codex Usage",
                                data={
                                    **self._pending_base_config,
                                    CONF_ACCESS_TOKEN: tokens["access_token"],
                                    CONF_REFRESH_TOKEN: tokens["refresh_token"],
                                    CONF_ID_TOKEN: tokens["id_token"],
                                    CONF_ACCOUNT_ID: tokens.get("account_id")
                                    or self._pending_base_config.get(CONF_ACCOUNT_ID, ""),
                                },
                            )

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
