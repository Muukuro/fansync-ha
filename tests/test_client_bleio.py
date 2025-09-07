import asyncio
import pytest
from custom_components.fansync_ble.client import FanState, FanSyncBleClient
from custom_components.fansync_ble.const import CONTROL_FAN_STATUS, RETURN_FAN_STATUS


def checksum9(arr: bytes) -> int:
    return sum(arr[:9]) & 0xFF


def make_return(speed=1, direction=0, up=0, down=0, tlo=0, thi=0, ftype=0):
    buf = bytearray([0x53, RETURN_FAN_STATUS, speed, direction, up, down, tlo, thi, ftype])
    buf.append(checksum9(buf))
    return bytes(buf)


class DummyClient:
    def __init__(self):
        self.writes = []
        self.connected = False
        self.notifies = []

    async def connect(self, timeout=15.0):
        self.connected = True

    async def get_services(self):
        return None

    async def start_notify(self, uuid, cb):
        self.notifies.append(uuid)
        # immediately simulate a RETURN frame arriving; handle async callback
        res = cb(uuid, bytearray(make_return(speed=2, down=25)))
        if asyncio.iscoroutine(res):
            await res

    async def stop_notify(self, uuid):
        pass

    async def write_gatt_char(self, uuid, payload, response=True):
        self.writes.append((uuid, bytes(payload), response))

    async def disconnect(self):
        self.connected = False


@pytest.mark.asyncio
async def test_set_speed_preserves_fields_and_assume_when_invalid(monkeypatch):
    # Patch BleakClient constructor used inside FanSyncBleClient to return DummyClient
    from custom_components.fansync_ble import client as client_mod

    dummy = DummyClient()
    monkeypatch.setattr(client_mod, "BleakClient", lambda addr: dummy)

    c = FanSyncBleClient("AA:BB")

    # Case 1: use provided valid state
    st = FanState.from_bytes(make_return(speed=1, direction=0, up=0, down=80, tlo=0x34, thi=0x12, ftype=9))
    await c.set_speed(3, st=st)
    # last write must be CONTROL frame with new speed 3 and preserved others
    assert dummy.writes, "no writes performed"
    _, payload, _ = dummy.writes[-1]
    assert payload[1] == CONTROL_FAN_STATUS
    assert payload[2] == 3
    assert payload[3] == st.direction
    assert payload[4] == st.up
    assert payload[5] == st.down
    assert payload[6] == st.timer_lo and payload[7] == st.timer_hi
    assert payload[8] == st.fan_type

    # Case 2: no state provided, client will attempt get_state (notify gives valid), then write
    dummy.writes.clear()
    await c.set_speed(2)
    _, payload2, _ = dummy.writes[-1]
    assert payload2[2] == 2
    # preserved from notify-produced state (speed 2 is replaced, but others preserved)
    assert payload2[5] == 25


@pytest.mark.asyncio
async def test_set_light_clamps_and_assumes_when_invalid(monkeypatch):
    from custom_components.fansync_ble import client as client_mod
    dummy = DummyClient()
    monkeypatch.setattr(client_mod, "BleakClient", lambda addr: dummy)

    c = FanSyncBleClient("AA:BB")

    # Provide invalid state (default FanState()) so fallback path is used
    await c.set_light(300, st=FanState())  # clamps to 100 and assume_speed default 1
    _, payload, _ = dummy.writes[-1]
    assert payload[1] == CONTROL_FAN_STATUS
    assert payload[2] == 1  # assume speed
    assert payload[5] == 100  # clamped

    # Valid state: preserve all but 'down'
    dummy.writes.clear()
    st = FanState.from_bytes(make_return(speed=2, direction=1, up=0, down=40, tlo=1, thi=0, ftype=7))
    await c.set_light(-5, st=st)  # clamps to 0
    _, payload2, _ = dummy.writes[-1]
    assert payload2[2] == st.speed
    assert payload2[3] == st.direction
    assert payload2[5] == 0
    assert payload2[8] == st.fan_type


@pytest.mark.asyncio
async def test_set_direction_preserves_or_assumes(monkeypatch):
    from custom_components.fansync_ble import client as client_mod
    dummy = DummyClient()
    monkeypatch.setattr(client_mod, "BleakClient", lambda addr: dummy)

    c = FanSyncBleClient("AA:BB")

    # Valid state preserves others
    st = FanState.from_bytes(make_return(speed=1, direction=0, down=10, tlo=2, thi=0, ftype=1))
    await c.set_direction(1, st=st)
    _, payload, _ = dummy.writes[-1]
    assert payload[2] == st.speed
    assert payload[3] == 1
    assert payload[5] == st.down

    # Invalid state -> assumes speed 1 and light 100
    dummy.writes.clear()
    await c.set_direction(0, st=FanState())
    _, payload2, _ = dummy.writes[-1]
    assert payload2[2] == 1
    assert payload2[3] == 0
    assert payload2[5] == 100


@pytest.mark.asyncio
async def test_discover_candidates_filters_by_name_hint(monkeypatch):
    # Prepare fake devices
    class Dev:
        def __init__(self, address, name):
            self.address = address
            self.name = name

    async def fake_discover(timeout=8.0):
        return [
            Dev("AA", "CeilingFan-123"),
            Dev("BB", "OtherDevice"),
            Dev("CC", None),
            Dev("DD", "ceiling-helper"),
        ]

    # Patch BleakScanner.discover inside module
    from custom_components.fansync_ble import client as client_mod
    monkeypatch.setattr(client_mod.BleakScanner, "discover", fake_discover)

    # No hint -> all with names
    res_all = await client_mod.discover_candidates(timeout=0.01)
    assert ("AA", "CeilingFan-123") in res_all
    assert ("BB", "OtherDevice") in res_all
    # Device with None name excluded
    assert not any(addr == "CC" for addr, _ in res_all)

    # Hint filters case-insensitively
    res_hint = await client_mod.discover_candidates(timeout=0.01, name_hint="Ceiling")
    assert ("AA", "CeilingFan-123") in res_hint
    assert ("DD", "ceiling-helper") in res_hint
    assert ("BB", "OtherDevice") not in res_hint
