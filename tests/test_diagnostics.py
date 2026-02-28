from types import SimpleNamespace

import pytest

from custom_components.fansync_ble.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_returns_coordinator_snapshot():
    class DummyCoordinator:
        def diagnostics_snapshot(self):
            return {"consecutive_failures": 2, "last_error": "timeout"}

    coord = DummyCoordinator()
    hass = SimpleNamespace()
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="FanSync Bluetooth (AA:BB)",
        options={"has_light": True},
        runtime_data=coord,
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["entry_id"] == "entry-1"
    assert diag["entry"]["options"]["has_light"] is True
    assert diag["coordinator"]["consecutive_failures"] == 2
