from __future__ import annotations
import asyncio
from dataclasses import dataclass
from bleak import BleakClient, BleakScanner
from .const import (
    WRITE_CHAR_UUID, NOTIFY_CHAR_UUID,
    GET_FAN_STATUS, CONTROL_FAN_STATUS, RETURN_FAN_STATUS,
)

def _checksum9(b: bytes | bytearray) -> int:
    return sum(b[:9]) & 0xFF

def build_frame(cmd_type:int, speed:int, direction:int, up:int, down:int, timer_lo:int, timer_hi:int, fan_type:int) -> bytes:
    arr = bytearray([0x53, cmd_type & 0xFF, speed & 0xFF, direction & 0xFF, up & 0xFF, down & 0xFF, timer_lo & 0xFF, timer_hi & 0xFF, fan_type & 0xFF])
    arr.append(_checksum9(arr))
    return bytes(arr)

@dataclass
class FanState:
    speed:int = 0
    direction:int = 0
    up:int = 0
    down:int = 0
    timer_lo:int = 0
    timer_hi:int = 0
    fan_type:int = 0
    valid:bool = False

    @classmethod
    def from_bytes(cls, data: bytes) -> "FanState":
        # Expect a 10-byte frame: 9 data bytes + 1 checksum
        if len(data) >= 10 and data[0] == 0x53 and data[1] == RETURN_FAN_STATUS:
            # Validate checksum to avoid accepting corrupted frames
            if _checksum9(data) == (data[9] & 0xFF):
                return cls(data[2], data[3], data[4], data[5], data[6], data[7], data[8], True)
        return cls()

    def minutes(self) -> int:
        return (self.timer_hi << 8) | self.timer_lo

async def discover_candidates(timeout: float = 8.0, name_hint: str | None = None):
    devices = await BleakScanner.discover(timeout=timeout)
    nh = (name_hint or "").lower()
    out = []
    for d in devices:
        if d.name and (nh in d.name.lower() if nh else True):
            out.append((d.address, d.name))
    return out

class FanSyncBleClient:
    def __init__(self, address: str, connect_retries: int = 3):
        self._address = address
        self._connect_retries = connect_retries

    async def _connect(self):
        last = None
        for _ in range(self._connect_retries):
            try:
                client = BleakClient(self._address)
                await client.connect(timeout=15.0)
                try:
                    if not getattr(client, "services", None):
                        getter = getattr(client, "get_services", None)
                        if getter:
                            await getter()
                except Exception:
                    pass
                return client
            except Exception as e:
                last = e
                await asyncio.sleep(0.8)
        raise last

    async def _ensure_notify(self, client: BleakClient, on_state):
        async def _cb(_, data: bytearray):
            st = FanState.from_bytes(bytes(data))
            if st.valid:
                on_state(st)
        try:
            await client.start_notify(NOTIFY_CHAR_UUID, _cb)
        except Exception:
            pass

    async def _write(self, client: BleakClient, payload: bytes):
        try:
            await client.write_gatt_char(WRITE_CHAR_UUID, payload, response=True)
        except Exception:
            await client.write_gatt_char(WRITE_CHAR_UUID, payload, response=False)

    async def get_state(self, timeout: float = 2.0) -> FanState:
        client = await self._connect()
        try:
            ev = asyncio.Event()
            state = FanState()
            def on_state(st: FanState):
                nonlocal state
                state = st
                ev.set()
            await self._ensure_notify(client, on_state)
            await asyncio.sleep(0.1)
            get = build_frame(GET_FAN_STATUS, 0, 0, 0, 0, 0, 0, 0)
            await self._write(client, get)
            try:
                await asyncio.wait_for(ev.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass
            return state
        finally:
            try:
                try:
                    await client.stop_notify(NOTIFY_CHAR_UUID)
                except Exception:
                    pass
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(0.4)

    async def set_speed(self, new_speed: int, st: FanState | None = None, assume_light: int | None = None):
        client = await self._connect()
        try:
            if not st:
                st = await self.get_state()
            if st.valid:
                frame = build_frame(CONTROL_FAN_STATUS, new_speed, st.direction, st.up, st.down, st.timer_lo, st.timer_hi, st.fan_type)
            else:
                if assume_light is None:
                    assume_light = 100
                frame = build_frame(CONTROL_FAN_STATUS, new_speed, 0, 0, max(0, min(100, assume_light)), 0, 0, 0)
            await self._write(client, frame)
            await asyncio.sleep(0.6)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(0.4)

    async def set_light(self, percent: int, st: FanState | None = None, assume_speed: int | None = None):
        client = await self._connect()
        try:
            if not st:
                st = await self.get_state()
            new_down = max(0, min(100, percent))
            if st.valid:
                frame = build_frame(CONTROL_FAN_STATUS, st.speed, st.direction, st.up, new_down, st.timer_lo, st.timer_hi, st.fan_type)
            else:
                if assume_speed is None:
                    assume_speed = 1
                frame = build_frame(CONTROL_FAN_STATUS, assume_speed, 0, 0, new_down, 0, 0, 0)
            await self._write(client, frame)
            await asyncio.sleep(0.6)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(0.4)

    async def set_direction(self, direction: int, st: FanState | None = None):
        client = await self._connect()
        try:
            if not st:
                st = await self.get_state()
            d = 1 if direction else 0
            if st.valid:
                frame = build_frame(CONTROL_FAN_STATUS, st.speed, d, st.up, st.down, st.timer_lo, st.timer_hi, st.fan_type)
            else:
                frame = build_frame(CONTROL_FAN_STATUS, 1, d, 0, 100, 0, 0, 0)
            await self._write(client, frame)
            await asyncio.sleep(0.6)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(0.4)
