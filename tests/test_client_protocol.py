from custom_components.fansync_ble.client import build_frame, FanState
from custom_components.fansync_ble.const import CONTROL_FAN_STATUS, RETURN_FAN_STATUS


def checksum9(arr: bytes) -> int:
    return sum(arr[:9]) & 0xFF


def make_return(speed=1, direction=0, up=0, down=0, tlo=0, thi=0, ftype=0):
    buf = bytearray(
        [0x53, RETURN_FAN_STATUS, speed, direction, up, down, tlo, thi, ftype]
    )
    buf.append(checksum9(buf))
    return bytes(buf)


def test_fanstate_rejects_wrong_header_and_cmd():
    # wrong header
    st1 = FanState.from_bytes(b"\x00" * 10)
    assert not st1.valid
    # wrong command
    bad = bytearray([0x53, CONTROL_FAN_STATUS, 1, 0, 0, 0, 0, 0, 0])
    bad.append(checksum9(bad))
    st2 = FanState.from_bytes(bytes(bad))
    assert not st2.valid
    # too short
    st3 = FanState.from_bytes(b"\x53\x32\x01")
    assert not st3.valid


def test_minutes_combines_hi_lo_correctly():
    st = FanState.from_bytes(make_return(tlo=0xFE, thi=0xAB))
    assert st.minutes() == (0xAB << 8) | 0xFE


def test_build_frame_positions_and_checksum_property_based():
    for speed in (0, 1, 2, 3, 250):
        for down in (0, 1, 50, 100, 200):
            f = build_frame(CONTROL_FAN_STATUS, speed, 1, 0, down, 0x34, 0x12, 0x05)
            assert f[0] == 0x53
            assert f[1] == CONTROL_FAN_STATUS
            assert f[2] == (speed & 0xFF)
            assert f[5] == (down & 0xFF)
            assert f[-1] == checksum9(f)


def test_fanstate_rejects_bad_checksum():
    # Build a RETURN-like frame but tamper checksum
    buf = bytearray([0x53, RETURN_FAN_STATUS, 1, 0, 0, 10, 0, 0, 0])
    bad = (checksum9(buf) + 1) & 0xFF
    buf.append(bad)
    st = FanState.from_bytes(bytes(buf))
    assert not st.valid
