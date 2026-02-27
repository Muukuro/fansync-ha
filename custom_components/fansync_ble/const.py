DOMAIN = "fansync_ble"

DEFAULT_NAME_HINT = "CeilingFan"

SERVICE_UUID = "0000e000-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000e001-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000e002-0000-1000-8000-00805f9b34fb"

# Frame command types
GET_FAN_STATUS = 0x30  # '0'
CONTROL_FAN_STATUS = 0x31  # '1'
RETURN_FAN_STATUS = 0x32  # '2'

# Options
CONF_HAS_LIGHT = "has_light"
CONF_DIMMABLE = "dimmable"
CONF_DIRECTION_SUPPORTED = "direction_supported"
CONF_POLL_INTERVAL = "poll_interval"
CONF_TURN_ON_SPEED = "turn_on_speed"

DEFAULT_HAS_LIGHT = True
DEFAULT_DIMMABLE = True
DEFAULT_DIRECTION_SUPPORTED = False
DEFAULT_POLL_INTERVAL = 15  # seconds
DEFAULT_TURN_ON_SPEED = 2  # medium
MIN_POLL_INTERVAL = 5
MAX_POLL_INTERVAL = 300
MIN_SPEED = 1
MAX_SPEED = 3


def normalize_poll_interval(value) -> int:
    """Normalize poll interval to a safe integer range."""
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return DEFAULT_POLL_INTERVAL
    return max(MIN_POLL_INTERVAL, min(MAX_POLL_INTERVAL, ivalue))


def normalize_turn_on_speed(value) -> int:
    """Normalize default turn-on speed to low/medium/high (1..3)."""
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TURN_ON_SPEED
    return max(MIN_SPEED, min(MAX_SPEED, ivalue))
