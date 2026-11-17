"""DataUpdateCoordinator for TESMart LAN integration."""
from __future__ import annotations

from collections.abc import Awaitable
from datetime import timedelta
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import TesmartLanClient, TesmartLanClientError
from .const import (
    CONF_MODEL,
    CONF_POLL_INTERVAL,
    DATA_ROUTES,
    DATA_SETTINGS,
    DEFAULT_MODEL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LOGGER,
    SETTING_AUTO_INPUT_DETECTION,
    SETTING_BUZZER_ENABLED,
    SETTING_FAN_MODE,
    SETTING_LED_TIMEOUT,
    SETTING_PRESET_SLOT,
    SUPPORTED_MODELS,
    UPDATE_INTERVAL_FALLBACK,
)

_T = TypeVar("_T")
_STORAGE_VERSION = 1


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

        model = str(entry.options.get(CONF_MODEL, entry.data.get(CONF_MODEL, DEFAULT_MODEL)))
        self._expected_outputs = SUPPORTED_MODELS.get(
            model, SUPPORTED_MODELS[DEFAULT_MODEL]
        )[1]
        self._store: Store[dict[str, object]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.settings"
        )
        self.client = TesmartLanClient(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
        )
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=entry,
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

    async def _async_setup(self) -> None:
        """Restore persisted (write-only) device settings."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            for key in self._settings:
                if key in stored:
                    self._settings[key] = stored[key]

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch latest device data."""
        try:
            routes = await self.client.get_routes(self._expected_outputs)
        except TesmartLanClientError as err:
            raise UpdateFailed(str(err)) from err
        return {
            DATA_ROUTES: routes,
            DATA_SETTINGS: self._settings.copy(),
        }

    @staticmethod
    async def _run(call: Awaitable[_T]) -> _T:
        """Await a client call, converting client errors to HomeAssistantError."""
        try:
            return await call
        except TesmartLanClientError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_set_buzzer_enabled(self, enabled: bool) -> None:
        """Set buzzer on/off."""
        await self._run(self.client.set_buzzer_enabled(enabled))
        self._settings[SETTING_BUZZER_ENABLED] = enabled
        self._push_settings()

    async def async_set_route(self, output: int, input_port: int) -> None:
        """Set one output route and refresh state."""
        await self._run(self.client.set_route(output=output, input_port=input_port))
        await self.async_refresh()

    async def async_set_all_outputs(self, input_port: int) -> None:
        """Set all outputs to one input and refresh state."""
        await self._run(self.client.set_all_outputs(input_port=input_port))
        await self.async_refresh()

    async def async_set_auto_input_detection(self, enabled: bool) -> None:
        """Set auto input detection."""
        await self._run(self.client.set_auto_input_detection(enabled))
        self._settings[SETTING_AUTO_INPUT_DETECTION] = enabled
        self._push_settings()

    async def async_set_led_timeout(self, option: str) -> None:
        """Set LED timeout option."""
        mapping = {"Off": 0, "10s": 10, "30s": 30}
        await self._run(self.client.set_led_timeout_seconds(mapping[option]))
        self._settings[SETTING_LED_TIMEOUT] = option
        self._push_settings()

    async def async_set_fan_mode(self, option: str) -> None:
        """Set fan mode option."""
        await self._run(self.client.set_fan_mode(option))
        self._settings[SETTING_FAN_MODE] = option
        self._push_settings()

    async def async_set_preset_slot(self, slot: str) -> None:
        """Store selected preset slot for actions."""
        self._settings[SETTING_PRESET_SLOT] = slot
        self._push_settings()

    async def async_mirror_outputs(self) -> None:
        """Mirror outputs and refresh route state."""
        await self._run(self.client.mirror_outputs())
        await self.async_refresh()

    async def async_load_preset(self, slot: int | None = None) -> None:
        """Load currently selected preset and refresh route state."""
        if slot is None:
            slot = int(self._settings[SETTING_PRESET_SLOT])
        else:
            self._settings[SETTING_PRESET_SLOT] = str(slot)
            self._push_settings()
        await self._run(self.client.load_preset(slot))
        await self.async_refresh()

    async def async_save_preset(self, slot: int | None = None) -> None:
        """Save current route state to currently selected preset."""
        if slot is None:
            slot = int(self._settings[SETTING_PRESET_SLOT])
        else:
            self._settings[SETTING_PRESET_SLOT] = str(slot)
            self._push_settings()
        await self._run(self.client.save_preset(slot))

    def _push_settings(self) -> None:
        """Push optimistic setting updates to entities."""
        data = dict(self.data or {})
        data[DATA_SETTINGS] = self._settings.copy()
        self._store.async_delay_save(lambda: self._settings.copy(), 1)
        self.async_set_updated_data(data)
