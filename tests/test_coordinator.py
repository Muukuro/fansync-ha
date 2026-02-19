from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest
from bleak.exc import BleakError

from custom_components.fansync_ble.client import FanState
from custom_components.fansync_ble.coordinator import FanSyncCoordinator


def _coord_without_init() -> FanSyncCoordinator:
    coord = FanSyncCoordinator.__new__(FanSyncCoordinator)
    coord.address = "AA:BB"
    coord.client = SimpleNamespace()
    coord._last_state = None
    coord._last_success_at = None
    coord._last_attempt_at = None
    coord._consecutive_failures = 0
    coord._last_error = None
    return coord


def test_async_apply_local_state_updates_state_and_notifies():
    coord = _coord_without_init()
    seen = {}

    def _capture(st):
        seen["state"] = st

    coord.async_set_updated_data = _capture
    coord.async_apply_local_state(speed=2, direction=1, down=75)

    assert coord._last_state is not None
    assert coord._last_state.valid is True
    assert coord._last_state.speed == 2
    assert coord._last_state.direction == 1
    assert coord._last_state.down == 75
    assert seen["state"] is coord._last_state


@pytest.mark.asyncio
async def test_async_schedule_immediate_refresh_creates_task():
    coord = _coord_without_init()
    marker = {"task": None}

    async def fake_refresh():
        return None

    def fake_create_task(coro):
        marker["task"] = coro
        return None

    coord.hass = SimpleNamespace(async_create_task=fake_create_task)
    coord.async_refresh = fake_refresh
    coord.async_schedule_immediate_refresh()

    assert marker["task"] is not None
    await marker["task"]


@pytest.mark.asyncio
async def test_update_data_timeout_keeps_last_state_and_tracks_failure():
    coord = _coord_without_init()
    coord._last_state = FanState(speed=1, valid=True)

    async def fake_get_state(timeout=4.0):
        raise asyncio.TimeoutError

    coord.client.get_state = fake_get_state
    st = await coord._async_update_data()

    assert st is coord._last_state
    assert coord._consecutive_failures == 1
    assert coord._last_error == "timeout"
    assert isinstance(coord._last_attempt_at, datetime)


@pytest.mark.asyncio
async def test_update_data_ble_error_keeps_last_state_and_tracks_failure():
    coord = _coord_without_init()
    coord._last_state = FanState(speed=2, valid=True)

    async def fake_get_state(timeout=4.0):
        raise BleakError("Not Found")

    coord.client.get_state = fake_get_state
    st = await coord._async_update_data()

    assert st is coord._last_state
    assert coord._consecutive_failures == 1
    assert coord._last_error == "Not Found"


@pytest.mark.asyncio
async def test_update_data_success_resets_failure_counters():
    coord = _coord_without_init()
    coord._consecutive_failures = 3
    coord._last_error = "timeout"

    async def fake_get_state(timeout=4.0):
        return FanState(speed=3, valid=True)

    coord.client.get_state = fake_get_state
    st = await coord._async_update_data()

    assert st is coord._last_state
    assert coord._last_state.speed == 3
    assert coord._consecutive_failures == 0
    assert coord._last_error is None
    assert isinstance(coord._last_success_at, datetime)
