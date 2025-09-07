from custom_components.fansync_ble.client import build_frame, FanState
from custom_components.fansync_ble.const import (
    GET_FAN_STATUS,
    CONTROL_FAN_STATUS,
    RETURN_FAN_STATUS,
)


def checksum9(arr: bytes) -> int:
    return sum(arr[:9]) & 0xFF


def test_build_get_frame_checksum_and_header():
    f_get = build_frame(GET_FAN_STATUS, 0, 0, 0, 0, 0, 0, 0)
    assert isinstance(f_get, (bytes, bytearray))
    assert len(f_get) == 10
    assert f_get[0] == 0x53
    assert f_get[-1] == checksum9(f_get)


def test_build_control_frame_checksum_and_position_fields():
    f_ctrl = build_frame(CONTROL_FAN_STATUS, 2, 1, 0, 75, 0x34, 0x12, 0x05)
    assert len(f_ctrl) == 10
    assert f_ctrl[1] == CONTROL_FAN_STATUS
    assert f_ctrl[2] == 2
    assert f_ctrl[3] == 1
    assert f_ctrl[4] == 0
    assert f_ctrl[5] == 75
    assert f_ctrl[6] == 0x34
    assert f_ctrl[7] == 0x12
    assert f_ctrl[8] == 0x05
    assert f_ctrl[-1] == checksum9(f_ctrl)


def test_fanstate_from_bytes_valid_and_minutes():
    # Build a fake RETURN frame (command 0x32) with timer 0x1234 and light 50
    payload = bytearray([0x53, RETURN_FAN_STATUS, 3, 1, 0, 50, 0x34, 0x12, 0x09])
    payload.append(checksum9(payload))
    st = FanState.from_bytes(bytes(payload))
    assert st.valid is True
    assert st.speed == 3
    assert st.direction == 1
    assert st.down == 50
    assert st.timer_lo == 0x34 and st.timer_hi == 0x12
    assert st.minutes() == 0x1234


def test_fanstate_from_bytes_invalid():
    bad = b"\x00" * 10
    st = FanState.from_bytes(bad)
    assert st.valid is False
