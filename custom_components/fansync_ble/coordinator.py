from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from bleak.exc import BleakError
from .client import FanSyncBleClient, FanState
from .const import DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FanSyncCoordinator(DataUpdateCoordinator):
    """Coordinator that periodically polls the fan state over BLE.

    Keeps the last known (possibly invalid) state to avoid flapping availability.
    """

    def __init__(
        self, hass: HomeAssistant, address: str, poll_interval: int | None = None
    ):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="fansync_ble",
            update_interval=timedelta(seconds=poll_interval or DEFAULT_POLL_INTERVAL),
        )
        self.client = FanSyncBleClient(address, hass=hass)
        self.address = address
        self._last_state: "FanState | None" = None

    async def _async_update_data(self):
        try:
            state = await self.client.get_state()
            # Only overwrite with a valid state; otherwise keep last known
            if getattr(state, "valid", False):
                self._last_state = state
            elif self._last_state is None:
                # If we have no previous state at all, store whatever we got
                self._last_state = state
        except BleakError as e:
            # Common transient issue: no available backend connection slot or device out of range
            msg = str(e)
            if "connection slot" in msg or "Not Found" in msg or "reach address" in msg:
                _LOGGER.debug(
                    "FanSync BLE update skipped due to transient BLE backend issue: %s",
                    msg,
                )
                return self._last_state
            _LOGGER.warning("FanSync BLE update failed: %s", msg)
            return self._last_state
        except Exception as e:  # safeguard against other transient issues
            _LOGGER.warning("FanSync BLE unexpected update error: %s", e)
            return self._last_state
        return self._last_state
