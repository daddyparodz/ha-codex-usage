"""Codex Usage integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import CodexUsageCoordinator

FALLBACK_SENSORS = {
    "sensor.codex_5h_used": ("primary_used_percent", "Codex 5h Used", "%", "mdi:timer-sand"),
    "sensor.codex_5h_remaining": ("primary_remaining_percent", "Codex 5h Remaining", "%", "mdi:timer-outline"),
    "sensor.codex_5h_reset": ("primary_reset_time", "Codex 5h Reset", None, "mdi:clock-outline"),
    "sensor.codex_weekly_used": ("secondary_used_percent", "Codex Weekly Used", "%", "mdi:calendar-week"),
    "sensor.codex_weekly_remaining": ("secondary_remaining_percent", "Codex Weekly Remaining", "%", "mdi:calendar-check"),
    "sensor.codex_weekly_reset": ("secondary_reset_time", "Codex Weekly Reset", None, "mdi:calendar-clock"),
    "sensor.codex_credits": ("credits_balance", "Codex Credits", None, "mdi:cash"),
    "sensor.codex_plan": ("plan", "Codex Plan", None, "mdi:account-badge"),
    "sensor.codex_limit_status": ("rate_limit_reached_type", "Codex Limit Status", None, "mdi:alert-circle"),
}


def _publish_fallback_states(hass: HomeAssistant, coordinator: CodexUsageCoordinator) -> None:
    data = coordinator.data or {}
    for entity_id, (key, name, unit, icon) in FALLBACK_SENSORS.items():
        value = data.get(key)
        attrs = {
            "friendly_name": name,
            "icon": icon,
            "last_update": data.get("last_update"),
        }
        if unit:
            attrs["unit_of_measurement"] = unit
        hass.states.async_set(entity_id, "unknown" if value is None else value, attrs)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Codex Usage from a config entry."""
    coordinator = CodexUsageCoordinator(hass, entry)
    await coordinator.async_refresh()

    unsub = coordinator.async_add_listener(lambda: _publish_fallback_states(hass, coordinator))
    _publish_fallback_states(hass, coordinator)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "unsub": unsub,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    stored = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if stored and stored.get("unsub"):
        stored["unsub"]()
    return unload_ok
