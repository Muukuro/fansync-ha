from __future__ import annotations
import asyncio
from dataclasses import dataclass
import inspect
from typing import Callable, Awaitable, Any
from bleak import BleakClient, BleakScanner

try:
    from bleak_retry_connector import establish_connection
except Exception:  # bleak-retry-connector may be provided by HA runtime
    establish_connection = None  # type: ignore
from .const import (
    WRITE_CHAR_UUID,
    NOTIFY_CHAR_UUID,
    GET_FAN_STATUS,
    CONTROL_FAN_STATUS,
    RETURN_FAN_STATUS,
)


def _checksum9(b: bytes | bytearray) -> int:
    """Compute checksum (sum of first 9 bytes & 0xFF) for 10-byte frames."""
    return sum(b[:9]) & 0xFF


def build_frame(
    cmd_type: int,
    speed: int,
    direction: int,
    up: int,
    down: int,
    timer_lo: int,
    timer_hi: int,
    fan_type: int,
) -> bytes:
    """Construct a 10-byte protocol frame with checksum.

    Layout: [0]=0x53, [1]=cmd, [2]=speed, [3]=direction, [4]=up, [5]=down,
            [6]=timerLo, [7]=timerHi, [8]=fanType, [9]=checksum.
    """
    arr = bytearray(
        [
            0x53,
            cmd_type & 0xFF,
            speed & 0xFF,
            direction & 0xFF,
            up & 0xFF,
            down & 0xFF,
            timer_lo & 0xFF,
            timer_hi & 0xFF,
            fan_type & 0xFF,
        ]
    )
    arr.append(_checksum9(arr))
    return bytes(arr)


@dataclass
class FanState:
    """In-memory representation of fan state parsed from RETURN frames."""

    speed: int = 0
    direction: int = 0
    up: int = 0
    down: int = 0
    timer_lo: int = 0
    timer_hi: int = 0
    fan_type: int = 0
    valid: bool = False

    @classmethod
    def from_bytes(cls, data: bytes) -> "FanState":
        """Parse a RETURN frame into a FanState, validating header, command, and checksum."""
        # Expect a 10-byte frame: 9 data bytes + 1 checksum
        if len(data) >= 10 and data[0] == 0x53 and data[1] == RETURN_FAN_STATUS:
            # Validate checksum to avoid accepting corrupted frames
            if _checksum9(data) == (data[9] & 0xFF):
                return cls(
                    data[2], data[3], data[4], data[5], data[6], data[7], data[8], True
                )
        return cls()

    def minutes(self) -> int:
        """Combine timer_hi/lo into minutes."""
        return (self.timer_hi << 8) | self.timer_lo


async def discover_candidates(
    timeout: float = 8.0, name_hint: str | None = None
) -> list[tuple[str, str]]:
    """Discover BLE devices and return (address, name) pairs, optionally filtered by name substring."""
    devices = await BleakScanner.discover(timeout=timeout)
    nh = (name_hint or "").lower()
    out: list[tuple[str, str]] = []
    for d in devices:
        if d.name and (nh in d.name.lower() if nh else True):
            out.append((d.address, d.name))
    return out


def _bleak_ctor_accepts_disconnected() -> bool:
    """Return True if BleakClient constructor accepts **kwargs (e.g., disconnected_callback).

    This informs whether bleak-retry-connector can pass extra keyword arguments safely.
    """
    try:
        sig = inspect.signature(BleakClient)
    except Exception:
        return False
    for p in sig.parameters.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return "disconnected_callback" in sig.parameters


class FanSyncBleClient:
    """Thin BLE client handling frame IO and short-lived sessions.

    Follows repository guideline: connect → GET/CONTROL → disconnect with small delays.
    """

    def __init__(self, address: str, connect_retries: int = 3, hass=None):
        self._address = address
        self._connect_retries = connect_retries
        # Optional Home Assistant context; if provided, we can use HA's Bluetooth helper
        self._hass = hass
        # Serialize BLE sessions to avoid overlapping command/poll connections.
        self._io_lock = asyncio.Lock()

    async def _establish_with_brc(self, target):
        """Establish connection via bleak-retry-connector handling signature variants.

        Tries multiple known signatures, always providing a stable name for logging/diagnostics.
        """
        if establish_connection is None:
            raise RuntimeError("bleak-retry-connector not available")
        name = f"fansync_ble_{self._address}"
        # Preferred HA signature: (hass, client_class, device_or_address, name=..., timeout=...)
        try:
            if self._hass is not None:
                return await establish_connection(
                    self._hass, BleakClient, target, name=name, timeout=15.0
                )
        except TypeError:
            # Fall through to other signatures
            pass
        # Signature with keyword name: (client_class, device_or_address, name=..., timeout=...)
        try:
            return await establish_connection(
                BleakClient, target, name=name, timeout=15.0
            )
        except TypeError:
            pass
        # Signature with positional name: (client_class, device_or_address, name, timeout=...)
        try:
            return await establish_connection(BleakClient, target, name, timeout=15.0)
        except TypeError:
            pass
        # Old signatures without name
        return await establish_connection(BleakClient, target, timeout=15.0)

    async def _connect(self):
        last = None
        for _ in range(self._connect_retries):
            try:
                if establish_connection is not None:
                    # Prefer HA bluetooth helper to resolve BLEDevice if hass is provided
                    dev = None
                    if self._hass is not None:
                        try:
                            # Import lazily to avoid hard dependency outside HA
                            from homeassistant.components import bluetooth as ha_bt  # type: ignore

                            dev = ha_bt.async_ble_device_from_address(
                                self._hass, self._address, connectable=True
                            )
                        except Exception:
                            dev = None
                    if dev is None:
                        # Fall back to BleakScanner lookup
                        try:
                            dev = await BleakScanner.find_device_by_address(
                                self._address, timeout=5.0
                            )
                        except Exception:
                            dev = None
                    # Use bleak-retry-connector when available AND the BleakClient ctor supports
                    # the extra kwargs that the connector forwards (like disconnected_callback).
                    use_brc = _bleak_ctor_accepts_disconnected()
                    if use_brc and dev is not None:
                        client = await self._establish_with_brc(dev)
                    elif use_brc:
                        # Pass address directly; bleak-retry-connector resolves and retries internally
                        client = await self._establish_with_brc(self._address)
                    else:
                        # Fallback for test stubs or environments without compatible BleakClient signature
                        client = BleakClient(self._address)
                        await client.connect(timeout=15.0)
                else:
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

    async def _ensure_notify(
        self,
        client: BleakClient,
        on_state: Callable[[FanState], Any] | Callable[[FanState], Awaitable[Any]],
    ):
        """Start notify for RETURN frames and forward valid states to callback.

        Broad exception handling is intentional: some backends may not support notifications
        or may intermittently fail. In such cases we proceed with a best-effort GET.
        """

        async def _cb(_, data: bytearray):
            st = FanState.from_bytes(bytes(data))
            if st.valid:
                res = on_state(st)
                if asyncio.iscoroutine(res):
                    await res

        try:
            await client.start_notify(NOTIFY_CHAR_UUID, _cb)
        except Exception:
            # Notification not critical for get_state fallback; ignore.
            pass

    async def _write(self, client: BleakClient, payload: bytes) -> None:
        """Write payload to the device, trying with response then without as fallback."""
        try:
            await client.write_gatt_char(WRITE_CHAR_UUID, payload, response=True)
        except Exception:
            await client.write_gatt_char(WRITE_CHAR_UUID, payload, response=False)

    async def _get_state_unlocked(self, timeout: float = 2.0) -> FanState:
        """Fetch current state via GET + notify, with timeout fallback.

        Returns a FanState (valid=False if nothing received within timeout).
        """
        client = await self._connect()
        try:
            ev = asyncio.Event()
            state = FanState()

            def on_state(st: FanState) -> None:
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
                # bleak-retry-connector returns a client compatible with BleakClient API
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(0.4)

    async def get_state(self, timeout: float = 2.0) -> FanState:
        async with self._io_lock:
            return await self._get_state_unlocked(timeout=timeout)

    async def set_speed(
        self,
        new_speed: int,
        st: FanState | None = None,
        assume_light: int | None = None,
    ) -> None:
        async with self._io_lock:
            if not st:
                st = await self._get_state_unlocked()
            client = await self._connect()
            try:
                if st.valid:
                    frame = build_frame(
                        CONTROL_FAN_STATUS,
                        new_speed,
                        st.direction,
                        st.up,
                        st.down,
                        st.timer_lo,
                        st.timer_hi,
                        st.fan_type,
                    )
                else:
                    if assume_light is None:
                        assume_light = 100
                    frame = build_frame(
                        CONTROL_FAN_STATUS,
                        new_speed,
                        0,
                        0,
                        max(0, min(100, assume_light)),
                        0,
                        0,
                        0,
                    )
                await self._write(client, frame)
                await asyncio.sleep(0.6)
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            await asyncio.sleep(0.4)

    async def set_light(
        self, percent: int, st: FanState | None = None, assume_speed: int | None = None
    ) -> None:
        async with self._io_lock:
            if not st:
                st = await self._get_state_unlocked()
            client = await self._connect()
            try:
                new_down = max(0, min(100, percent))
                if st.valid:
                    frame = build_frame(
                        CONTROL_FAN_STATUS,
                        st.speed,
                        st.direction,
                        st.up,
                        new_down,
                        st.timer_lo,
                        st.timer_hi,
                        st.fan_type,
                    )
                else:
                    if assume_speed is None:
                        assume_speed = 1
                    frame = build_frame(
                        CONTROL_FAN_STATUS, assume_speed, 0, 0, new_down, 0, 0, 0
                    )
                await self._write(client, frame)
                await asyncio.sleep(0.6)
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            await asyncio.sleep(0.4)

    async def set_direction(self, direction: int, st: FanState | None = None) -> None:
        async with self._io_lock:
            if not st:
                st = await self._get_state_unlocked()
            client = await self._connect()
            try:
                d = 1 if direction else 0
                if st.valid:
                    frame = build_frame(
                        CONTROL_FAN_STATUS,
                        st.speed,
                        d,
                        st.up,
                        st.down,
                        st.timer_lo,
                        st.timer_hi,
                        st.fan_type,
                    )
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
