"""DataUpdateCoordinator for TESMart LAN integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import TesmartLanClient, TesmartLanClientError
from .const import (
    CONF_POLL_INTERVAL,
    DATA_AVAILABLE,
    DATA_ROUTES,
    DATA_SETTINGS,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LOGGER,
    SETTING_AUTO_INPUT_DETECTION,
    SETTING_BUZZER_ENABLED,
    SETTING_FAN_MODE,
    SETTING_LED_TIMEOUT,
    SETTING_PRESET_SLOT,
    UPDATE_INTERVAL_FALLBACK,
)


class TesmartLanCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """TESMart state coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.config_entry = entry
        poll_interval = entry.options.get(
            CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        )
        try:
            interval = timedelta(seconds=int(poll_interval))
        except (TypeError, ValueError):
            interval = UPDATE_INTERVAL_FALLBACK

        self.client = TesmartLanClient(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
        )
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{entry.data.get(CONF_NAME, entry.entry_id)}",
            update_interval=interval,
        )
        self._settings = {
            SETTING_BUZZER_ENABLED: True,
            SETTING_AUTO_INPUT_DETECTION: False,
            SETTING_LED_TIMEOUT: "Off",
            SETTING_FAN_MODE: "Auto",
            SETTING_PRESET_SLOT: "1",
        }

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch latest device data."""
        try:
            routes = await self.client.get_routes()
        except TesmartLanClientError as err:
            raise UpdateFailed(str(err)) from err
        return {
            DATA_ROUTES: routes,
            DATA_AVAILABLE: True,
            DATA_SETTINGS: self._settings.copy(),
        }

    async def async_set_buzzer_enabled(self, enabled: bool) -> None:
        """Set buzzer on/off."""
        await self.client.set_buzzer_enabled(enabled)
        self._settings[SETTING_BUZZER_ENABLED] = enabled
        self._push_settings()

    async def async_set_route(self, output: int, input_port: int) -> None:
        """Set one output route and refresh state."""
        await self.client.set_route(output=output, input_port=input_port)
        await self.async_request_refresh()

    async def async_set_all_outputs(self, input_port: int) -> None:
        """Set all outputs to one input and refresh state."""
        await self.client.set_all_outputs(input_port=input_port)
        await self.async_request_refresh()

    async def async_set_auto_input_detection(self, enabled: bool) -> None:
        """Set auto input detection."""
        await self.client.set_auto_input_detection(enabled)
        self._settings[SETTING_AUTO_INPUT_DETECTION] = enabled
        self._push_settings()

    async def async_set_led_timeout(self, option: str) -> None:
        """Set LED timeout option."""
        mapping = {"Off": 0, "10s": 10, "30s": 30}
        await self.client.set_led_timeout_seconds(mapping[option])
        self._settings[SETTING_LED_TIMEOUT] = option
        self._push_settings()

    async def async_set_fan_mode(self, option: str) -> None:
        """Set fan mode option."""
        await self.client.set_fan_mode(option)
        self._settings[SETTING_FAN_MODE] = option
        self._push_settings()

    async def async_set_preset_slot(self, slot: str) -> None:
        """Store selected preset slot for actions."""
        self._settings[SETTING_PRESET_SLOT] = slot
        self._push_settings()

    async def async_mirror_outputs(self) -> None:
        """Mirror outputs and refresh route state."""
        await self.client.mirror_outputs()
        await self.async_request_refresh()

    async def async_load_preset(self, slot: int | None = None) -> None:
        """Load currently selected preset and refresh route state."""
        if slot is None:
            slot = int(self._settings[SETTING_PRESET_SLOT])
        else:
            self._settings[SETTING_PRESET_SLOT] = str(slot)
            self._push_settings()
        await self.client.load_preset(slot)
        await self.async_request_refresh()

    async def async_save_preset(self, slot: int | None = None) -> None:
        """Save current route state to currently selected preset."""
        if slot is None:
            slot = int(self._settings[SETTING_PRESET_SLOT])
        else:
            self._settings[SETTING_PRESET_SLOT] = str(slot)
            self._push_settings()
        await self.client.save_preset(slot)

    def _push_settings(self) -> None:
        """Push optimistic setting updates to entities."""
        data = dict(self.data or {})
        data[DATA_SETTINGS] = self._settings.copy()
        self.async_set_updated_data(data)
