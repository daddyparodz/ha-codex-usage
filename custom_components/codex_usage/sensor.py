"""Sensor platform for Codex Usage."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CodexUsageCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CodexSensorDescription(SensorEntityDescription):
    object_id: str


SENSORS = [
    CodexSensorDescription(
        key="primary_used_percent",
        name="Codex 5h Used",
        object_id="codex_5h_used",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:timer-sand",
    ),
    CodexSensorDescription(
        key="primary_remaining_percent",
        name="Codex 5h Remaining",
        object_id="codex_5h_remaining",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:timer-outline",
    ),
    CodexSensorDescription(
        key="primary_reset_time",
        name="Codex 5h Reset",
        object_id="codex_5h_reset",
        icon="mdi:clock-outline",
    ),
    CodexSensorDescription(
        key="secondary_used_percent",
        name="Codex Weekly Used",
        object_id="codex_weekly_used",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:calendar-week",
    ),
    CodexSensorDescription(
        key="secondary_remaining_percent",
        name="Codex Weekly Remaining",
        object_id="codex_weekly_remaining",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:calendar-check",
    ),
    CodexSensorDescription(
        key="secondary_reset_time",
        name="Codex Weekly Reset",
        object_id="codex_weekly_reset",
        icon="mdi:calendar-clock",
    ),
    CodexSensorDescription(
        key="credits_balance",
        name="Codex Credits",
        object_id="codex_credits",
        icon="mdi:cash",
    ),
    CodexSensorDescription(
        key="plan",
        name="Codex Plan",
        object_id="codex_plan",
        icon="mdi:account-badge",
    ),
    CodexSensorDescription(
        key="rate_limit_reached_type",
        name="Codex Limit Status",
        object_id="codex_limit_status",
        icon="mdi:alert-circle",
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
    entities = [CodexUsageSensor(coordinator, entry, desc) for desc in SENSORS]
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
        desc: CodexSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        self._entry_id = entry.entry_id
        self._attr_unique_id = desc.object_id
        self._attr_name = desc.name
        self._attr_suggested_object_id = desc.object_id

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
