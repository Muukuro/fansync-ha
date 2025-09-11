from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN,
    DEFAULT_NAME_HINT,
    CONF_HAS_LIGHT,
    CONF_DIMMABLE,
    CONF_DIRECTION_SUPPORTED,
    CONF_POLL_INTERVAL,
    DEFAULT_HAS_LIGHT,
    DEFAULT_DIMMABLE,
    DEFAULT_DIRECTION_SUPPORTED,
    DEFAULT_POLL_INTERVAL,
)
from .client import discover_candidates


class FanSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow to set up FanSync BLE integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        # If user submitted the form, validate
        if user_input is not None:
            address = (user_input.get("address") or "").strip()
            if not address:
                errors["base"] = "address_required"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                # Build options from submitted fields
                options = {
                    CONF_HAS_LIGHT: user_input.get(CONF_HAS_LIGHT, DEFAULT_HAS_LIGHT),
                    CONF_DIMMABLE: user_input.get(CONF_DIMMABLE, DEFAULT_DIMMABLE),
                    CONF_DIRECTION_SUPPORTED: user_input.get(
                        CONF_DIRECTION_SUPPORTED, DEFAULT_DIRECTION_SUPPORTED
                    ),
                    CONF_POLL_INTERVAL: user_input.get(
                        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                    ),
                }
                return self.async_create_entry(
                    title=f"FanSync BLE ({address})",
                    data={"address": address},
                    options=options,
                )

        # Try to discover nearby devices (best-effort)
        devices = []
        discovery_error = None
        try:
            devices = await discover_candidates(
                timeout=8.0, name_hint=DEFAULT_NAME_HINT
            )
        except Exception:
            discovery_error = "bluetooth_unavailable"

        # Build selection list (address only for now)
        choices = [addr for addr, _ in devices]

        # If no devices found or discovery failed: show a free-text field with helpful error and options
        if not choices:
            schema = vol.Schema(
                {
                    vol.Required("address", default=""): str,
                    vol.Required(CONF_HAS_LIGHT, default=DEFAULT_HAS_LIGHT): bool,
                    vol.Required(CONF_DIMMABLE, default=DEFAULT_DIMMABLE): bool,
                    vol.Required(
                        CONF_DIRECTION_SUPPORTED, default=DEFAULT_DIRECTION_SUPPORTED
                    ): bool,
                    vol.Required(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): int,
                }
            )
            if discovery_error:
                errors["base"] = discovery_error
            else:
                # Only set this if not already set due to validation
                errors.setdefault("base", "no_devices_found")
            return self.async_show_form(
                step_id="user", data_schema=schema, errors=errors
            )

        # Devices found: present a dropdown plus options
        schema = vol.Schema(
            {
                vol.Required("address"): vol.In(choices),
                vol.Required(CONF_HAS_LIGHT, default=DEFAULT_HAS_LIGHT): bool,
                vol.Required(CONF_DIMMABLE, default=DEFAULT_DIMMABLE): bool,
                vol.Required(
                    CONF_DIRECTION_SUPPORTED, default=DEFAULT_DIRECTION_SUPPORTED
                ): bool,
                vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FanSyncOptionsFlowHandler(config_entry)


class FanSyncOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to adjust entity capabilities and polling interval."""

    def __init__(self, config_entry):
        # Avoid assigning to deprecated attribute; store locally
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HAS_LIGHT, default=opts.get(CONF_HAS_LIGHT, DEFAULT_HAS_LIGHT)
                ): bool,
                vol.Required(
                    CONF_DIMMABLE, default=opts.get(CONF_DIMMABLE, DEFAULT_DIMMABLE)
                ): bool,
                vol.Required(
                    CONF_DIRECTION_SUPPORTED,
                    default=opts.get(
                        CONF_DIRECTION_SUPPORTED, DEFAULT_DIRECTION_SUPPORTED
                    ),
                ): bool,
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=opts.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
