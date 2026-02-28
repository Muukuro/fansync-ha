from __future__ import annotations
from typing import TYPE_CHECKING
from .const import CONF_POLL_INTERVAL, normalize_poll_interval

if TYPE_CHECKING:
    # Only import HA types for type checking; avoid runtime dependency during tests
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry

PLATFORMS: list[str] = ["fan", "light"]


async def async_setup_entry(hass: "HomeAssistant", entry: "ConfigEntry"):
    # Lazy import to avoid importing Home Assistant dependencies at module import time
    from .coordinator import FanSyncCoordinator

    address = entry.data["address"]
    poll = entry.options.get(CONF_POLL_INTERVAL) if entry.options else None
    coord = FanSyncCoordinator(
        hass, address, poll_interval=normalize_poll_interval(poll)
    )
    await coord.async_config_entry_first_refresh()
    entry.runtime_data = coord

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entities when options change (e.g., dimmable flag)
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    return True


async def async_unload_entry(hass: "HomeAssistant", entry: "ConfigEntry"):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None
    return unload_ok


async def async_options_updated(hass: "HomeAssistant", entry: "ConfigEntry"):
    await hass.config_entries.async_reload(entry.entry_id)
