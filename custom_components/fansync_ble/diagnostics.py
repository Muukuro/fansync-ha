from __future__ import annotations

from typing import TYPE_CHECKING

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: "HomeAssistant", config_entry: "ConfigEntry"
) -> dict:
    """Return diagnostics for a config entry."""
    coord = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "entry": {
            "entry_id": config_entry.entry_id,
            "title": config_entry.title,
            "has_options": bool(config_entry.options),
            "options": dict(config_entry.options),
        },
        "coordinator": coord.diagnostics_snapshot(),
    }
