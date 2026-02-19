from custom_components.fansync_ble.const import (
    DEFAULT_POLL_INTERVAL,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
    normalize_poll_interval,
)


def test_normalize_poll_interval_defaults_for_invalid_values():
    assert normalize_poll_interval(None) == DEFAULT_POLL_INTERVAL
    assert normalize_poll_interval("not-an-int") == DEFAULT_POLL_INTERVAL


def test_normalize_poll_interval_clamps_to_bounds():
    assert normalize_poll_interval(MIN_POLL_INTERVAL - 1) == MIN_POLL_INTERVAL
    assert normalize_poll_interval(MAX_POLL_INTERVAL + 1) == MAX_POLL_INTERVAL


def test_normalize_poll_interval_accepts_valid_values():
    assert normalize_poll_interval(MIN_POLL_INTERVAL) == MIN_POLL_INTERVAL
    assert normalize_poll_interval("42") == 42
    assert normalize_poll_interval(MAX_POLL_INTERVAL) == MAX_POLL_INTERVAL
