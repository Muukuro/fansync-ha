from __future__ import annotations
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import (
    DOMAIN,
    CONF_DIRECTION_SUPPORTED,
    CONF_TURN_ON_SPEED,
    DEFAULT_TURN_ON_SPEED,
    normalize_turn_on_speed,
)
from .client import FanState

_DIRECTION_FEATURE = getattr(
    FanEntityFeature, "SET_DIRECTION", FanEntityFeature.DIRECTION
)
_TURN_ON_FEATURE = getattr(FanEntityFeature, "TURN_ON", 0)
_TURN_OFF_FEATURE = getattr(FanEntityFeature, "TURN_OFF", 0)


class FanSyncFan(FanEntity):
    _attr_has_entity_name = True
    _attr_name = "Ceiling Fan"
    _attr_speed_count = 3

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}-fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="FanSync BLE"
        )

        # Always advertise speed support via percentage. Add direction if enabled.
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | _TURN_ON_FEATURE | _TURN_OFF_FEATURE
        )
        if entry.options.get(CONF_DIRECTION_SUPPORTED, False):
            self._attr_supported_features |= _DIRECTION_FEATURE

    @property
    def available(self):
        st = self.coordinator._last_state
        return st is not None and st.valid

    @property
    def is_on(self):
        st: FanState | None = self.coordinator._last_state
        return (getattr(st, "speed", 0) if st else 0) > 0

    @property
    def percentage(self):
        st: FanState | None = self.coordinator._last_state
        s = getattr(st, "speed", 0) if st else 0
        return 0 if s <= 0 else 33 if s == 1 else 66 if s == 2 else 100

    async def async_set_percentage(self, percentage: int) -> None:
        p = percentage or 0
        new_speed = 0 if p <= 0 else 1 if p <= 33 else 2 if p <= 66 else 3
        await self.coordinator.client.set_speed(
            new_speed, st=self.coordinator._last_state, assume_light=100
        )
        self.coordinator.async_apply_local_state(speed=new_speed)
        self.coordinator.async_schedule_immediate_refresh()

    async def async_turn_on(self, percentage: int | None = None, **kwargs) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            st = self.coordinator._last_state
            curr = getattr(st, "speed", 0) if st else 0
            default_speed = normalize_turn_on_speed(
                self.entry.options.get(CONF_TURN_ON_SPEED, DEFAULT_TURN_ON_SPEED)
            )
            target = default_speed if curr == 0 else curr
            await self.coordinator.client.set_speed(target, st=st, assume_light=100)
            self.coordinator.async_apply_local_state(speed=target)
            self.coordinator.async_schedule_immediate_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.set_speed(
            0, st=self.coordinator._last_state, assume_light=100
        )
        self.coordinator.async_apply_local_state(speed=0)
        self.coordinator.async_schedule_immediate_refresh()

    @property
    def current_direction(self):
        if not self.entry.options.get(CONF_DIRECTION_SUPPORTED, False):
            return None
        st = self.coordinator._last_state
        d = getattr(st, "direction", 0) if st else 0
        return "reverse" if d == 1 else "forward"

    async def async_set_direction(self, direction: str) -> None:
        if not self.entry.options.get(CONF_DIRECTION_SUPPORTED, False):
            return
        d = 1 if direction == "reverse" else 0
        await self.coordinator.client.set_direction(d, st=self.coordinator._last_state)
        self.coordinator.async_apply_local_state(direction=d)
        self.coordinator.async_schedule_immediate_refresh()

    async def async_update(self):
        await self.coordinator.async_refresh()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FanSyncFan(coord, entry)], update_before_add=True)
