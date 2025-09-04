from __future__ import annotations
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .client import FanSyncBleClient
from .const import DEFAULT_POLL_INTERVAL

class FanSyncCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, address: str, poll_interval: int | None = None):
        super().__init__(
            hass,
            logger=hass.helpers.logger.logger,
            name="fansync_ble",
            update_interval=timedelta(seconds=poll_interval or DEFAULT_POLL_INTERVAL),
        )
        self.client = FanSyncBleClient(address)
        self.address = address
        self._last_state = None

    async def _async_update_data(self):
        self._last_state = await self.client.get_state()
        return self._last_state
