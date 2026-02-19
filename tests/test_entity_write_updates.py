from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.fansync_ble.client import FanState
from custom_components.fansync_ble.const import CONF_DIMMABLE, CONF_DIRECTION_SUPPORTED
from custom_components.fansync_ble.fan import FanSyncFan
from custom_components.fansync_ble.light import FanSyncLight


class _DummyClient:
    def __init__(self):
        self.calls = []

    async def set_speed(self, speed, st=None, assume_light=None):
        self.calls.append(("set_speed", speed, st, assume_light))

    async def set_direction(self, direction, st=None):
        self.calls.append(("set_direction", direction, st))

    async def set_light(self, percent, st=None, assume_speed=None):
        self.calls.append(("set_light", percent, st, assume_speed))


class _DummyCoordinator:
    def __init__(self, state):
        self._last_state = state
        self.client = _DummyClient()
        self.local_updates = []
        self.refresh_scheduled = 0

    def async_apply_local_state(self, **kwargs):
        self.local_updates.append(kwargs)

    def async_schedule_immediate_refresh(self):
        self.refresh_scheduled += 1


def _entry(options):
    return SimpleNamespace(entry_id="entry-1", options=options)


@pytest.mark.asyncio
async def test_fan_set_percentage_applies_local_state_and_refresh():
    coord = _DummyCoordinator(FanState(speed=1, valid=True))
    ent = FanSyncFan(coord, _entry({CONF_DIRECTION_SUPPORTED: True}))

    await ent.async_set_percentage(100)

    assert coord.client.calls[0][0] == "set_speed"
    assert coord.client.calls[0][1] == 3
    assert coord.local_updates[-1] == {"speed": 3}
    assert coord.refresh_scheduled == 1


@pytest.mark.asyncio
async def test_fan_set_direction_applies_local_state_and_refresh():
    coord = _DummyCoordinator(FanState(speed=2, direction=0, valid=True))
    ent = FanSyncFan(coord, _entry({CONF_DIRECTION_SUPPORTED: True}))

    await ent.async_set_direction("reverse")

    assert coord.client.calls[0][0] == "set_direction"
    assert coord.client.calls[0][1] == 1
    assert coord.local_updates[-1] == {"direction": 1}
    assert coord.refresh_scheduled == 1


@pytest.mark.asyncio
async def test_light_turn_on_dimmable_updates_down_and_refresh():
    coord = _DummyCoordinator(FanState(speed=2, down=10, valid=True))
    ent = FanSyncLight(coord, _entry({CONF_DIMMABLE: True}))

    await ent.async_turn_on(brightness=128)

    assert coord.client.calls[0][0] == "set_light"
    assert coord.local_updates[-1]["down"] == int(128 * 100 / 255)
    assert coord.local_updates[-1]["speed"] is None
    assert coord.refresh_scheduled == 1


@pytest.mark.asyncio
async def test_light_turn_off_without_valid_state_sets_assumed_speed():
    coord = _DummyCoordinator(FanState(valid=False))
    ent = FanSyncLight(coord, _entry({CONF_DIMMABLE: False}))

    await ent.async_turn_off()

    assert coord.client.calls[0][0] == "set_light"
    assert coord.local_updates[-1] == {"down": 0, "speed": 0}
    assert coord.refresh_scheduled == 1
