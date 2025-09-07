from __future__ import annotations
from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_DIMMABLE, CONF_HAS_LIGHT
from .client import FanState

class FanSyncLight(LightEntity):
    _attr_has_entity_name = True
    _attr_name = "Fan Light"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}-light"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="FanSync BLE")

        if entry.options.get(CONF_DIMMABLE, True):
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def available(self):
        st = self.coordinator._last_state
        return st is not None and st.valid

    @property
    def is_on(self):
        st: FanState | None = self.coordinator._last_state
        return (getattr(st, "down", 0) if st else 0) > 0

    @property
    def brightness(self):
        if not self.entry.options.get(CONF_DIMMABLE, True):
            return 255 if self.is_on else 0
        st = self.coordinator._last_state
        return int((getattr(st, "down", 0) if st else 0) * 255 / 100)

    async def async_turn_on(self, **kwargs):
        dimmable = self.entry.options.get(CONF_DIMMABLE, True)
        if dimmable:
            bri = kwargs.get("brightness", 255)
            percent = int(bri * 100 / 255)
            percent = max(1, percent)  # avoid 0 when turning on
        else:
            percent = 100  # on/off only
        await self.coordinator.client.set_light(percent, st=self.coordinator._last_state, assume_speed=1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.client.set_light(0, st=self.coordinator._last_state, assume_speed=0)
        await self.coordinator.async_request_refresh()

    async def async_update(self):
        await self.coordinator.async_request_refresh()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    # Only add light entity if enabled in options
    if entry.options.get(CONF_HAS_LIGHT, True):
        async_add_entities([FanSyncLight(coord, entry)], update_before_add=True)
