import asyncio
import pytest

from custom_components.fansync_ble.client import FanState, FanSyncBleClient


@pytest.mark.asyncio
async def test_set_speed_commands_are_serialized(monkeypatch):
    active_sessions = 0
    max_concurrent = 0

    class DummyConnection:
        async def disconnect(self):
            nonlocal active_sessions
            active_sessions -= 1

    async def fake_connect(self):
        nonlocal active_sessions, max_concurrent
        active_sessions += 1
        max_concurrent = max(max_concurrent, active_sessions)
        await asyncio.sleep(0)
        return DummyConnection()

    async def fake_write(self, client, payload):
        await asyncio.sleep(0)

    async def fast_sleep(_seconds):
        return None

    monkeypatch.setattr(FanSyncBleClient, "_connect", fake_connect)
    monkeypatch.setattr(FanSyncBleClient, "_write", fake_write)
    monkeypatch.setattr(
        "custom_components.fansync_ble.client.asyncio.sleep", fast_sleep
    )

    c = FanSyncBleClient("AA:BB")
    st = FanState(valid=True)

    await asyncio.gather(
        c.set_speed(1, st=st),
        c.set_speed(2, st=st),
        c.set_speed(3, st=st),
    )

    assert max_concurrent == 1
