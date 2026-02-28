from __future__ import annotations
from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_DIMMABLE, CONF_HAS_LIGHT
from .client import FanState
from .entity import FanSyncBaseEntity


class FanSyncLight(FanSyncBaseEntity, LightEntity):
    _attr_name = "Fan Light"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, object_id_suffix="light")

        if entry.options.get(CONF_DIMMABLE, True):
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

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
        st = self.coordinator._last_state
        await self.coordinator.client.set_light(percent, st=st, assume_speed=1)
        speed = None if (st and st.valid) else 1
        self.coordinator.async_apply_local_state(down=percent, speed=speed)
        self.coordinator.async_schedule_immediate_refresh()

    async def async_turn_off(self, **kwargs):
        st = self.coordinator._last_state
        await self.coordinator.client.set_light(0, st=st, assume_speed=0)
        speed = None if (st and st.valid) else 0
        self.coordinator.async_apply_local_state(down=0, speed=speed)
        self.coordinator.async_schedule_immediate_refresh()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    # Only add light entity if enabled in options
    if entry.options.get(CONF_HAS_LIGHT, True):
        async_add_entities([FanSyncLight(coord, entry)], update_before_add=True)
