"""Button entities for TESMart LAN actions."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TesmartLanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up button entities from config entry."""
    coordinator: TesmartLanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TesmartMirrorButton(coordinator, entry),
            TesmartLoadPresetButton(coordinator, entry),
            TesmartSavePresetButton(coordinator, entry),
        ]
    )


class TesmartBaseButton(CoordinatorEntity[TesmartLanCoordinator], ButtonEntity):
    """Base TESMart button entity."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize base button."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="TESmart",
            name=entry.data[CONF_NAME],
            model="LAN Matrix",
        )


class TesmartMirrorButton(TesmartBaseButton):
    """Mirror routing button."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize mirror button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Mirror Outputs"
        self._attr_unique_id = f"{entry.entry_id}_mirror_outputs"
        self._attr_icon = "mdi:call-split"

    async def async_press(self) -> None:
        """Mirror matrix outputs."""
        await self.coordinator.async_mirror_outputs()


class TesmartLoadPresetButton(TesmartBaseButton):
    """Load selected preset button."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize load button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Load Preset"
        self._attr_unique_id = f"{entry.entry_id}_load_preset"
        self._attr_icon = "mdi:folder-download"

    async def async_press(self) -> None:
        """Load selected preset."""
        await self.coordinator.async_load_preset()


class TesmartSavePresetButton(TesmartBaseButton):
    """Save selected preset button."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize save button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Save Preset"
        self._attr_unique_id = f"{entry.entry_id}_save_preset"
        self._attr_icon = "mdi:content-save"

    async def async_press(self) -> None:
        """Save selected preset."""
        await self.coordinator.async_save_preset()
