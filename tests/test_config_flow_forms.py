from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("voluptuous")

from custom_components.fansync_ble import config_flow as cfg
from custom_components.fansync_ble.client import FanState
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

AbortFlow = pytest.importorskip("homeassistant.data_entry_flow").AbortFlow


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


@pytest.mark.asyncio
async def test_config_flow_submit_blank_address_shows_address_required(monkeypatch):
    async def no_devices(timeout=8.0, name_hint=None):
        return []

    monkeypatch.setattr(cfg, "discover_candidates", no_devices)
    flow = FanSyncConfigFlow()

    res = await flow.async_step_user(
        {
            "address": "   ",
            CONF_HAS_LIGHT: True,
            CONF_DIMMABLE: True,
            CONF_DIRECTION_SUPPORTED: False,
            CONF_POLL_INTERVAL: 15,
            CONF_TURN_ON_SPEED: 2,
        }
    )
    assert res["type"] == "form"
    assert res["errors"]["base"] == "address_required"


@pytest.mark.asyncio
async def test_config_flow_submit_valid_creates_entry_with_options(monkeypatch):
    async def no_devices(timeout=8.0, name_hint=None):
        return []

    class OkClient:
        def __init__(self, address, hass=None):
            self.address = address
            self.hass = hass

        async def get_state(self, timeout=3.0):
            return FanState(valid=True)

    monkeypatch.setattr(cfg, "discover_candidates", no_devices)
    monkeypatch.setattr(cfg, "FanSyncBleClient", OkClient)

    flow = FanSyncConfigFlow()
    flow._abort_if_unique_id_configured = lambda: None

    async def _set_unique_id(_uid):
        return None

    flow.async_set_unique_id = _set_unique_id

    res = await flow.async_step_user(
        {
            "address": "AA:BB:CC:DD:EE:FF",
            CONF_HAS_LIGHT: False,
            CONF_DIMMABLE: False,
            CONF_DIRECTION_SUPPORTED: True,
            CONF_POLL_INTERVAL: 21,
            CONF_TURN_ON_SPEED: 3,
        }
    )
    assert res["type"] == "create_entry"
    assert res["data"] == {"address": "AA:BB:CC:DD:EE:FF"}
    assert res["options"][CONF_HAS_LIGHT] is False
    assert res["options"][CONF_DIMMABLE] is False
    assert res["options"][CONF_DIRECTION_SUPPORTED] is True
    assert res["options"][CONF_POLL_INTERVAL] == 21
    assert res["options"][CONF_TURN_ON_SPEED] == 3


@pytest.mark.asyncio
async def test_config_flow_submit_shows_cannot_connect_on_failed_probe(monkeypatch):
    async def no_devices(timeout=8.0, name_hint=None):
        return []

    class FailingClient:
        def __init__(self, address, hass=None):
            self.address = address
            self.hass = hass

        async def get_state(self, timeout=3.0):
            raise RuntimeError("boom")

    monkeypatch.setattr(cfg, "discover_candidates", no_devices)
    monkeypatch.setattr(cfg, "FanSyncBleClient", FailingClient)

    flow = FanSyncConfigFlow()
    flow._abort_if_unique_id_configured = lambda: None

    async def _set_unique_id(_uid):
        return None

    flow.async_set_unique_id = _set_unique_id

    res = await flow.async_step_user(
        {
            "address": "AA:BB:CC:DD:EE:FF",
            CONF_HAS_LIGHT: True,
            CONF_DIMMABLE: True,
            CONF_DIRECTION_SUPPORTED: False,
            CONF_POLL_INTERVAL: 15,
            CONF_TURN_ON_SPEED: 2,
        }
    )
    assert res["type"] == "form"
    assert res["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_config_flow_submit_duplicate_unique_id_aborts(monkeypatch):
    async def no_devices(timeout=8.0, name_hint=None):
        return []

    monkeypatch.setattr(cfg, "discover_candidates", no_devices)
    flow = FanSyncConfigFlow()

    async def _set_unique_id(_uid):
        return None

    def _abort():
        raise AbortFlow("already_configured")

    flow.async_set_unique_id = _set_unique_id
    flow._abort_if_unique_id_configured = _abort

    with pytest.raises(AbortFlow):
        await flow.async_step_user(
            {
                "address": "AA:BB",
                CONF_HAS_LIGHT: True,
                CONF_DIMMABLE: True,
                CONF_DIRECTION_SUPPORTED: False,
                CONF_POLL_INTERVAL: 15,
                CONF_TURN_ON_SPEED: 2,
            }
        )


@pytest.mark.asyncio
async def test_options_flow_submit_creates_entry():
    config_entry = SimpleNamespace(options={})
    flow = FanSyncOptionsFlowHandler(config_entry)

    user_input = {
        CONF_HAS_LIGHT: True,
        CONF_DIMMABLE: True,
        CONF_DIRECTION_SUPPORTED: False,
        CONF_POLL_INTERVAL: 15,
        CONF_TURN_ON_SPEED: 2,
    }
    res = await flow.async_step_init(user_input)

    assert res["type"] == "create_entry"
    assert res["data"] == user_input
