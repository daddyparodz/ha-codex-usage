"""Sensor platform for Codex Usage."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CodexUsageCoordinator
from .reset_credits import parse_timestamp

_LOGGER = logging.getLogger(__name__)

SENSORS = [
    (
        SensorEntityDescription(
            key="primary_used_percent",
            name="Codex 5h Used",
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:timer-sand",
        ),
        "codex_5h_used",
    ),
    (
        SensorEntityDescription(
            key="primary_remaining_percent",
            name="Codex 5h Remaining",
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:timer-outline",
        ),
        "codex_5h_remaining",
    ),
    (
        SensorEntityDescription(
            key="primary_reset_time",
            name="Codex 5h Reset",
            icon="mdi:clock-outline",
        ),
        "codex_5h_reset",
    ),
    (
        SensorEntityDescription(
            key="secondary_used_percent",
            name="Codex Weekly Used",
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:calendar-week",
        ),
        "codex_weekly_used",
    ),
    (
        SensorEntityDescription(
            key="secondary_remaining_percent",
            name="Codex Weekly Remaining",
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:calendar-check",
        ),
        "codex_weekly_remaining",
    ),
    (
        SensorEntityDescription(
            key="secondary_reset_time",
            name="Codex Weekly Reset",
            icon="mdi:calendar-clock",
        ),
        "codex_weekly_reset",
    ),
    (
        SensorEntityDescription(
            key="credits_balance",
            name="Codex Credits",
            icon="mdi:cash",
        ),
        "codex_credits",
    ),
    (
        SensorEntityDescription(
            key="plan",
            name="Codex Plan",
            icon="mdi:account-badge",
        ),
        "codex_plan",
    ),
    (
        SensorEntityDescription(
            key="rate_limit_reached_type",
            name="Codex Limit Status",
            icon="mdi:alert-circle",
        ),
        "codex_limit_status",
    ),
    (
        SensorEntityDescription(
            key="reset_credits_available",
            name="Codex Resets Available",
            icon="mdi:restore-alert",
        ),
        "codex_resets_available",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    # Compatibility fallback: some HA versions/extensions may not expose
    # runtime_data on ConfigEntry in platform setup.
    coordinator: CodexUsageCoordinator = getattr(entry, "runtime_data", None) or hass.data[
        DOMAIN
    ][entry.entry_id]
    entities = [
        CodexUsageSensor(coordinator, entry, desc, object_id) for desc, object_id in SENSORS
    ]
    _LOGGER.debug("Adding %s codex_usage sensor entities", len(entities))
    async_add_entities(entities)

    known_reset_credit_ids: set[str] = set()

    def _add_new_reset_credit_entities() -> None:
        new_entities = []
        for credit in (coordinator.data or {}).get("reset_credits", []):
            credit_id = credit.get("id")
            if not isinstance(credit_id, str) or credit_id in known_reset_credit_ids:
                continue
            known_reset_credit_ids.add(credit_id)
            new_entities.append(CodexResetCreditSensor(coordinator, entry, credit_id))

        if new_entities:
            _LOGGER.debug("Adding %s Codex reset-credit entities", len(new_entities))
            async_add_entities(new_entities)

    _add_new_reset_credit_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_reset_credit_entities))


class CodexUsageSensor(CoordinatorEntity[CodexUsageCoordinator], SensorEntity):
    """Representation of a Codex usage sensor."""

    _attr_has_entity_name = False
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: CodexUsageCoordinator,
        entry: ConfigEntry,
        desc: SensorEntityDescription,
        object_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        self._entry_id = entry.entry_id
        self._attr_unique_id = object_id
        self._attr_name = desc.name
        self._attr_suggested_object_id = object_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Codex Usage",
            manufacturer="OpenAI",
            model="Codex Usage Integration",
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        attributes = {"last_update": data.get("last_update")}
        if self.entity_description.key == "reset_credits_available":
            attributes.update(
                {
                    "credits": data.get("reset_credits", []),
                    "next_expiration": data.get("reset_credits_next_expiration"),
                    "credits_last_update": data.get("reset_credits_last_update"),
                    "error": data.get("reset_credits_error"),
                }
            )
        return attributes


class CodexResetCreditSensor(CoordinatorEntity[CodexUsageCoordinator], SensorEntity):
    """One timestamp entity for each individual Codex reset credit."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:restore-clock"

    def __init__(
        self,
        coordinator: CodexUsageCoordinator,
        entry: ConfigEntry,
        credit_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._credit_id = credit_id
        self._attr_unique_id = f"codex_reset_credit_{credit_id}"
        self._attr_suggested_object_id = f"codex_reset_credit_{credit_id}"
        self._attr_name = self._display_name

    @property
    def _credit(self) -> dict | None:
        for credit in (self.coordinator.data or {}).get("reset_credits", []):
            if credit.get("id") == self._credit_id:
                return credit
        return None

    @property
    def _display_name(self) -> str:
        credit = self._credit
        granted_at = parse_timestamp(credit.get("granted_at") if credit else None)
        if granted_at:
            return f"Codex Reset Credit {granted_at.strftime('%Y-%m-%d %H:%M UTC')}"
        return f"Codex Reset Credit {self._credit_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Codex Usage",
            manufacturer="OpenAI",
            model="Codex Usage Integration",
        )

    @property
    def available(self) -> bool:
        return super().available and self._credit is not None

    @property
    def native_value(self):
        credit = self._credit
        return parse_timestamp(credit.get("expires_at") if credit else None)

    @property
    def extra_state_attributes(self):
        credit = self._credit or {}
        return {
            "granted_at": credit.get("granted_at"),
            "expires_at": credit.get("expires_at"),
            "status": credit.get("status"),
            "remaining": credit.get("remaining"),
            "credits_last_update": (self.coordinator.data or {}).get(
                "reset_credits_last_update"
            ),
        }
