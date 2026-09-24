"""Calendar platform for Codex reset events."""

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
from .weekly_reset_calendar import build_weekly_reset_event


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Codex calendar entities."""
    coordinator: CodexUsageCoordinator = getattr(entry, "runtime_data", None) or hass.data[
        DOMAIN
    ][entry.entry_id]
    async_add_entities(
        [
            CodexResetCreditsCalendar(coordinator, entry),
            CodexWeeklyResetCalendar(coordinator, entry),
        ]
    )


class CodexResetCreditsCalendar(
    CoordinatorEntity[CodexUsageCoordinator], CalendarEntity
):
    """Calendar containing usable banked-reset expirations."""

    _attr_has_entity_name = False
    _attr_name = "Banked Resets"
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
        data = build_reset_credit_events(
            (self.coordinator.data or {}).get("reset_credits", [])
        )
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
        """Return banked-reset events overlapping the requested range."""
        data = build_reset_credit_events(
            (self.coordinator.data or {}).get("reset_credits", [])
        )
        return [
            CalendarEvent(**event)
            for event in events_in_range(data, start_date, end_date)
        ]


class CodexWeeklyResetCalendar(
    CoordinatorEntity[CodexUsageCoordinator], CalendarEntity
):
    """Calendar containing the next weekly usage-window reset."""

    _attr_has_entity_name = False
    _attr_name = "Weekly Reset"
    _attr_icon = "mdi:calendar-week"
    _attr_unique_id = "codex_weekly_reset_calendar"
    _attr_suggested_object_id = "codex_weekly_reset"

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
    def _weekly_event(self) -> CalendarEvent | None:
        event = build_weekly_reset_event(
            (self.coordinator.data or {}).get("weekly_reset_epoch")
        )
        return CalendarEvent(**event) if event else None

    @property
    def event(self) -> CalendarEvent | None:
        event = self._weekly_event
        if event is None or event.end <= datetime.now(tz=UTC):
            return None
        return event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return the weekly-reset event when it overlaps the requested range."""
        event = self._weekly_event
        if event is None:
            return []
        if event.end <= start_date or event.start >= end_date:
            return []
        return [event]
