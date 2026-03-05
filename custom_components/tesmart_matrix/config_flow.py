"""Config flow for TESMart LAN integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.helpers import selector

from .client import TesmartLanClient, TesmartLanClientCommunicationError, TesmartLanClientError
from .const import (
    CONF_MODEL,
    CONF_POLL_INTERVAL,
    DEFAULT_MODEL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    LOGGER,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
    SUPPORTED_MODELS,
)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Schema for initial integration setup."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "TESMart Matrix")): selector.TextSelector(),
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): selector.TextSelector(),
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_MODEL, default=defaults.get(CONF_MODEL, DEFAULT_MODEL)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(SUPPORTED_MODELS.keys()),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_POLL_INTERVAL,
                    max=MAX_POLL_INTERVAL,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _options_schema(config_entry: config_entries.ConfigEntry) -> vol.Schema:
    """Schema for options flow."""
    options = config_entry.options
    data = config_entry.data
    return vol.Schema(
        {
            vol.Required(
                CONF_MODEL,
                default=options.get(CONF_MODEL, data.get(CONF_MODEL, DEFAULT_MODEL)),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(SUPPORTED_MODELS.keys()),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_POLL_INTERVAL,
                default=options.get(CONF_POLL_INTERVAL, data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_POLL_INTERVAL,
                    max=MAX_POLL_INTERVAL,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


class TesmartLanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TESMart LAN."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle initial setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = int(user_input[CONF_PORT])

            try:
                client = TesmartLanClient(host=host, port=port)
                await client.get_routes()
            except TesmartLanClientCommunicationError:
                errors["base"] = "cannot_connect"
            except TesmartLanClientError:
                LOGGER.exception("TESMart setup validation failed for %s:%s", host, port)
                errors["base"] = "unknown"
            else:
                user_input[CONF_PORT] = port
                user_input[CONF_MODEL] = str(user_input[CONF_MODEL])
                user_input[CONF_POLL_INTERVAL] = int(user_input[CONF_POLL_INTERVAL])
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_user_schema(user_input), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Create options flow."""
        return TesmartLanOptionsFlow()


class TesmartLanOptionsFlow(config_entries.OptionsFlow):
    """Handle TESMart options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        if user_input is not None:
            user_input[CONF_MODEL] = str(user_input[CONF_MODEL])
            user_input[CONF_POLL_INTERVAL] = int(user_input[CONF_POLL_INTERVAL])
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry),
        )
