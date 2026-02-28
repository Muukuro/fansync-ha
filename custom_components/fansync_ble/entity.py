from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .client import FanState


class FanSyncBaseEntity(Entity):
    """Shared entity behavior for FanSync platforms."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, *, object_id_suffix: str) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}-{object_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="FanSync Bluetooth"
        )

    @property
    def available(self) -> bool:
        st: FanState | None = self.coordinator._last_state
        return st is not None and st.valid

    async def async_update(self) -> None:
        await self.coordinator.async_refresh()
