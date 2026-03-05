"""Select entities for TESMart LAN."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MODEL,
    DATA_ROUTES,
    DATA_SETTINGS,
    DEFAULT_MODEL,
    DOMAIN,
    SETTING_FAN_MODE,
    SETTING_LED_TIMEOUT,
    SETTING_PRESET_SLOT,
    SUPPORTED_MODELS,
)
from .coordinator import TesmartLanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up select entities from config entry."""
    coordinator: TesmartLanCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = str(entry.options.get(CONF_MODEL, entry.data.get(CONF_MODEL, DEFAULT_MODEL)))
    input_count, output_count = SUPPORTED_MODELS.get(model, SUPPORTED_MODELS[DEFAULT_MODEL])

    entities: list[SelectEntity] = [
        TesmartAllOutputsSelect(coordinator, entry, input_count),
        TesmartLedTimeoutSelect(coordinator, entry),
        TesmartFanModeSelect(coordinator, entry),
        TesmartPresetSlotSelect(coordinator, entry),
    ]
    entities.extend(
        TesmartOutputSelect(coordinator, entry, output, input_count)
        for output in range(1, output_count + 1)
    )
    async_add_entities(entities)


class TesmartBaseSelect(CoordinatorEntity[TesmartLanCoordinator], SelectEntity):
    """Base select with common device info."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="TESmart",
            name=entry.data[CONF_NAME],
            model="LAN Matrix",
        )


class TesmartOutputSelect(TesmartBaseSelect):
    """Select entity for one output routing."""

    def __init__(
        self,
        coordinator: TesmartLanCoordinator,
        entry: ConfigEntry,
        output_number: int,
        input_count: int,
    ) -> None:
        """Initialize output route selector."""
        super().__init__(coordinator, entry)
        self._output_number = output_number
        self._attr_name = f"Output {output_number} Source"
        self._attr_unique_id = f"{entry.entry_id}_output_{output_number}"
        self._attr_options = [str(item) for item in range(1, input_count + 1)]

    @property
    def current_option(self) -> str | None:
        """Current input for this output."""
        data = self.coordinator.data or {}
        routes: dict[int, int] = data.get(DATA_ROUTES, {})
        selected = routes.get(self._output_number)
        return str(selected) if selected else None

    async def async_select_option(self, option: str) -> None:
        """Set output route."""
        await self.coordinator.async_set_route(self._output_number, int(option))


class TesmartAllOutputsSelect(TesmartBaseSelect):
    """Select entity that routes all outputs to one input."""

    def __init__(
        self, coordinator: TesmartLanCoordinator, entry: ConfigEntry, input_count: int
    ) -> None:
        """Initialize all-outputs selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "All Outputs Source"
        self._attr_unique_id = f"{entry.entry_id}_all_outputs"
        self._attr_options = [str(item) for item in range(1, input_count + 1)]

    @property
    def current_option(self) -> str | None:
        """Current global source when all outputs match."""
        data = self.coordinator.data or {}
        routes: dict[int, int] = data.get(DATA_ROUTES, {})
        if not routes:
            return None

        distinct_inputs = {input_port for input_port in routes.values()}
        if len(distinct_inputs) != 1:
            return None
        return str(next(iter(distinct_inputs)))

    async def async_select_option(self, option: str) -> None:
        """Route all outputs to selected input."""
        await self.coordinator.async_set_all_outputs(int(option))


class TesmartLedTimeoutSelect(TesmartBaseSelect):
    """LED timeout selector."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize LED timeout selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "LED Timeout"
        self._attr_unique_id = f"{entry.entry_id}_led_timeout"
        self._attr_options = ["Off", "10s", "30s"]
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        """Current LED timeout option."""
        data = self.coordinator.data or {}
        settings: dict[str, object] = data.get(DATA_SETTINGS, {})
        return str(settings.get(SETTING_LED_TIMEOUT, "Off"))

    async def async_select_option(self, option: str) -> None:
        """Set LED timeout option."""
        await self.coordinator.async_set_led_timeout(option)


class TesmartFanModeSelect(TesmartBaseSelect):
    """Fan mode selector (experimental)."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize fan mode selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "Fan Mode"
        self._attr_unique_id = f"{entry.entry_id}_fan_mode"
        self._attr_options = ["Auto", "Low", "High"]
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        """Current fan mode option."""
        data = self.coordinator.data or {}
        settings: dict[str, object] = data.get(DATA_SETTINGS, {})
        return str(settings.get(SETTING_FAN_MODE, "Auto"))

    async def async_select_option(self, option: str) -> None:
        """Set fan mode option."""
        await self.coordinator.async_set_fan_mode(option)


class TesmartPresetSlotSelect(TesmartBaseSelect):
    """Preset slot selector (used by load/save preset buttons)."""

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize preset slot selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "Preset Slot"
        self._attr_unique_id = f"{entry.entry_id}_preset_slot"
        self._attr_options = [str(item) for item in range(1, 9)]
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        """Current preset slot option."""
        data = self.coordinator.data or {}
        settings: dict[str, object] = data.get(DATA_SETTINGS, {})
        return str(settings.get(SETTING_PRESET_SLOT, "1"))

    async def async_select_option(self, option: str) -> None:
        """Set current preset slot."""
        await self.coordinator.async_set_preset_slot(option)
