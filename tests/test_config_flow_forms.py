from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("voluptuous")

from custom_components.fansync_ble import config_flow as cfg
from custom_components.fansync_ble.config_flow import (
    FanSyncConfigFlow,
    FanSyncOptionsFlowHandler,
)
from custom_components.fansync_ble.const import (
    CONF_DIMMABLE,
    CONF_DIRECTION_SUPPORTED,
    CONF_HAS_LIGHT,
    CONF_POLL_INTERVAL,
    CONF_TURN_ON_SPEED,
)


@pytest.mark.asyncio
async def test_config_flow_discovery_error_shows_bluetooth_unavailable(monkeypatch):
    async def boom(timeout=8.0, name_hint=None):
        raise RuntimeError("no bt")

    monkeypatch.setattr(cfg, "discover_candidates", boom)
    flow = FanSyncConfigFlow()

    res = await flow.async_step_user(None)
    assert res["type"] == "form"
    assert res["errors"]["base"] == "bluetooth_unavailable"


@pytest.mark.asyncio
async def test_config_flow_no_devices_shows_no_devices_found(monkeypatch):
    async def no_devices(timeout=8.0, name_hint=None):
        return []

    monkeypatch.setattr(cfg, "discover_candidates", no_devices)
    flow = FanSyncConfigFlow()

    res = await flow.async_step_user(None)
    assert res["type"] == "form"
    assert res["errors"]["base"] == "no_devices_found"


@pytest.mark.asyncio
async def test_config_flow_devices_found_uses_choice_schema(monkeypatch):
    async def found(timeout=8.0, name_hint=None):
        return [("AA:BB", "CeilingFan-A"), ("CC:DD", "CeilingFan-B")]

    monkeypatch.setattr(cfg, "discover_candidates", found)
    flow = FanSyncConfigFlow()

    res = await flow.async_step_user(None)
    assert res["type"] == "form"

    schema = res["data_schema"]
    normalized = schema(
        {
            "address": "CC:DD",
            CONF_HAS_LIGHT: True,
            CONF_DIMMABLE: False,
            CONF_DIRECTION_SUPPORTED: True,
            CONF_POLL_INTERVAL: 15,
            CONF_TURN_ON_SPEED: 3,
        }
    )
    assert normalized["address"] == "CC:DD"
    assert normalized[CONF_TURN_ON_SPEED] == 3

    with pytest.raises(Exception):
        schema(
            {
                "address": "EE:FF",
                CONF_HAS_LIGHT: True,
                CONF_DIMMABLE: False,
                CONF_DIRECTION_SUPPORTED: True,
                CONF_POLL_INTERVAL: 15,
                CONF_TURN_ON_SPEED: 3,
            }
        )


@pytest.mark.asyncio
async def test_options_flow_schema_defaults_reflect_entry_options():
    config_entry = SimpleNamespace(
        options={
            CONF_HAS_LIGHT: False,
            CONF_DIMMABLE: False,
            CONF_DIRECTION_SUPPORTED: True,
            CONF_POLL_INTERVAL: 42,
            CONF_TURN_ON_SPEED: 1,
        }
    )
    flow = FanSyncOptionsFlowHandler(config_entry)

    res = await flow.async_step_init(None)
    assert res["type"] == "form"
    schema = res["data_schema"]

    normalized = schema({})
    assert normalized[CONF_HAS_LIGHT] is False
    assert normalized[CONF_DIMMABLE] is False
    assert normalized[CONF_DIRECTION_SUPPORTED] is True
    assert normalized[CONF_POLL_INTERVAL] == 42
    assert normalized[CONF_TURN_ON_SPEED] == 1
