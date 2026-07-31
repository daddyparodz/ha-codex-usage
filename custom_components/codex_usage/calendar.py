"""Calendar platform for Codex reset credits."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CodexUsageCoordinator
from .reset_calendar import build_reset_credit_events, events_in_range


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the Codex reset-credit calendar."""
    coordinator: CodexUsageCoordinator = getattr(entry, "runtime_data", None) or hass.data[
        DOMAIN
    ][entry.entry_id]
    async_add_entities([CodexResetCreditsCalendar(coordinator, entry)])


class CodexResetCreditsCalendar(CoordinatorEntity[CodexUsageCoordinator], CalendarEntity):
    """One automatically updated calendar containing all usable reset credits."""

    _attr_has_entity_name = False
    _attr_name = "Codex Reset Credits"
    _attr_icon = "mdi:calendar-refresh"
    _attr_unique_id = "codex_reset_credits_calendar"
    _attr_suggested_object_id = "codex_reset_credits"

    def __init__(self, coordinator: CodexUsageCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Codex Usage",
            manufacturer="OpenAI",
            model="Codex Usage Integration",
        )

    @property
    def _events(self) -> list[CalendarEvent]:
        data = build_reset_credit_events((self.coordinator.data or {}).get("reset_credits", []))
        return [CalendarEvent(**event) for event in data]

    @property
    def event(self) -> CalendarEvent | None:
        now = datetime.now(tz=UTC)
        future = [event for event in self._events if event.end > now]
        if not future:
            return None
        return min(
            future,
            key=lambda event: (
                event.start > now,
                event.start if event.start > now else event.end,
            ),
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return reset-credit events overlapping the requested time range."""
        data = build_reset_credit_events((self.coordinator.data or {}).get("reset_credits", []))
        return [CalendarEvent(**event) for event in events_in_range(data, start_date, end_date)]
