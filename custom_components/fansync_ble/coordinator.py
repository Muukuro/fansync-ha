from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .client import FanSyncBleClient
from .const import DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

class FanSyncCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, address: str, poll_interval: int | None = None):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="fansync_ble",
            update_interval=timedelta(seconds=poll_interval or DEFAULT_POLL_INTERVAL),
        )
        self.client = FanSyncBleClient(address)
        self.address = address
        self._last_state = None

    async def _async_update_data(self):
        self._last_state = await self.client.get_state()
        return self._last_state
