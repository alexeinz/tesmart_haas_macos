"""Switch entities for TESMart LAN."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_SETTINGS,
    DOMAIN,
    SETTING_AUTO_INPUT_DETECTION,
    SETTING_BUZZER_ENABLED,
)
from .coordinator import TesmartLanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up switch entities from config entry."""
    coordinator: TesmartLanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TesmartBuzzerSwitch(coordinator, entry),
            TesmartAutoInputSwitch(coordinator, entry),
        ]
    )


class TesmartBaseSwitch(CoordinatorEntity[TesmartLanCoordinator], SwitchEntity):
    """Base TESMart switch entity."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize base switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="TESmart",
            name=entry.data[CONF_NAME],
            model="LAN Matrix",
        )

    def _setting_bool(self, key: str, default: bool = False) -> bool:
        data = self.coordinator.data or {}
        settings: dict[str, object] = data.get(DATA_SETTINGS, {})
        value = settings.get(key, default)
        return bool(value)


class TesmartBuzzerSwitch(TesmartBaseSwitch):
    """Buzzer control switch."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize buzzer switch."""
        super().__init__(coordinator, entry)
        self._attr_name = "Buzzer Enabled"
        self._attr_unique_id = f"{entry.entry_id}_buzzer_enabled"
        self._attr_icon = "mdi:volume-high"

    @property
    def is_on(self) -> bool | None:
        """Switch state."""
        return self._setting_bool(SETTING_BUZZER_ENABLED, default=True)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable buzzer."""
        await self.coordinator.async_set_buzzer_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable buzzer."""
        await self.coordinator.async_set_buzzer_enabled(False)


class TesmartAutoInputSwitch(TesmartBaseSwitch):
    """Auto input detection switch."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize auto input switch."""
        super().__init__(coordinator, entry)
        self._attr_name = "Auto Input Detection"
        self._attr_unique_id = f"{entry.entry_id}_auto_input_detection"
        self._attr_icon = "mdi:refresh-auto"

    @property
    def is_on(self) -> bool | None:
        """Switch state."""
        return self._setting_bool(SETTING_AUTO_INPUT_DETECTION, default=False)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable auto input detection."""
        await self.coordinator.async_set_auto_input_detection(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable auto input detection."""
        await self.coordinator.async_set_auto_input_detection(False)
