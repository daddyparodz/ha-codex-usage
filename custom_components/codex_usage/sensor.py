"""Sensor platform for Codex Usage."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CodexUsageCoordinator

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
        return {"last_update": data.get("last_update")}
