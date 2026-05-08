"""Sensor platform for Codex Usage."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CodexUsageCoordinator


@dataclass(frozen=True)
class CodexSensorDescription:
    key: str
    name: str
    unit: str | None = None
    icon: str | None = None


SENSORS = [
    CodexSensorDescription("primary_used_percent", "Codex 5h Used", PERCENTAGE, "mdi:timer-sand"),
    CodexSensorDescription("primary_remaining_percent", "Codex 5h Remaining", PERCENTAGE, "mdi:timer-outline"),
    CodexSensorDescription("primary_reset_time", "Codex 5h Reset", None, "mdi:clock-outline"),
    CodexSensorDescription("secondary_used_percent", "Codex Weekly Used", PERCENTAGE, "mdi:calendar-week"),
    CodexSensorDescription("secondary_remaining_percent", "Codex Weekly Remaining", PERCENTAGE, "mdi:calendar-check"),
    CodexSensorDescription("secondary_reset_time", "Codex Weekly Reset", None, "mdi:calendar-clock"),
    CodexSensorDescription("credits_balance", "Codex Credits", None, "mdi:cash"),
    CodexSensorDescription("plan", "Codex Plan", None, "mdi:account-badge"),
    CodexSensorDescription("rate_limit_reached_type", "Codex Limit Status", None, "mdi:alert-circle"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CodexUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(CodexUsageSensor(coordinator, entry, desc) for desc in SENSORS)


class CodexUsageSensor(CoordinatorEntity[CodexUsageCoordinator], SensorEntity):
    """Representation of a Codex usage sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CodexUsageCoordinator, entry: ConfigEntry, desc: CodexSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        self._attr_unique_id = f"{entry.entry_id}_{desc.key}"
        self._attr_name = desc.name
        self._attr_icon = desc.icon
        self._attr_native_unit_of_measurement = desc.unit

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self):
        return {"last_update": self.coordinator.data.get("last_update")}
