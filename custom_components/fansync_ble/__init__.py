from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_POLL_INTERVAL
from .coordinator import FanSyncCoordinator

PLATFORMS: list[str] = ["fan", "light"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    address = entry.data["address"]
    poll = entry.options.get(CONF_POLL_INTERVAL) if entry.options else None
    coord = FanSyncCoordinator(hass, address, poll_interval=poll)
    await coord.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entities when options change (e.g., dimmable flag)
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
