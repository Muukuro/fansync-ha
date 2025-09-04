from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, DEFAULT_NAME_HINT,
    CONF_HAS_LIGHT, CONF_DIMMABLE, CONF_DIRECTION_SUPPORTED, CONF_POLL_INTERVAL,
    DEFAULT_HAS_LIGHT, DEFAULT_DIMMABLE, DEFAULT_DIRECTION_SUPPORTED, DEFAULT_POLL_INTERVAL,
)
from .client import discover_candidates

class FanSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None and "address" in user_input and user_input["address"]:
            await self.async_set_unique_id(user_input["address"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"FanSync BLE ({user_input.get('name','device')})",
                data={"address": user_input["address"], "name": user_input.get("name")},
                options={
                    CONF_HAS_LIGHT: DEFAULT_HAS_LIGHT,
                    CONF_DIMMABLE: DEFAULT_DIMMABLE,
                    CONF_DIRECTION_SUPPORTED: DEFAULT_DIRECTION_SUPPORTED,
                    CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                }
            )

        devices = await discover_candidates(timeout=8.0, name_hint=DEFAULT_NAME_HINT)
        # Build selection list (address only for now)
        choices = [addr for addr, _ in devices]
        if not choices:
            choices = [""]

        schema = vol.Schema({
            vol.Required("address"): vol.In(choices),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FanSyncOptionsFlowHandler(config_entry)

class FanSyncOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema({
            vol.Required(CONF_HAS_LIGHT, default=opts.get(CONF_HAS_LIGHT, DEFAULT_HAS_LIGHT)): bool,
            vol.Required(CONF_DIMMABLE, default=opts.get(CONF_DIMMABLE, DEFAULT_DIMMABLE)): bool,
            vol.Required(CONF_DIRECTION_SUPPORTED, default=opts.get(CONF_DIRECTION_SUPPORTED, DEFAULT_DIRECTION_SUPPORTED)): bool,
            vol.Required(CONF_POLL_INTERVAL, default=opts.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)): int,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
