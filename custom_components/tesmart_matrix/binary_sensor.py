"""Binary sensor entities for TESMart LAN status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DATA_ROUTES, DEFAULT_MODEL, DOMAIN, SUPPORTED_MODELS
from .coordinator import TesmartLanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up binary sensors from config entry."""
    coordinator: TesmartLanCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = str(entry.options.get(CONF_MODEL, entry.data.get(CONF_MODEL, DEFAULT_MODEL)))
    input_count, output_count = SUPPORTED_MODELS.get(model, SUPPORTED_MODELS[DEFAULT_MODEL])

    entities: list[BinarySensorEntity] = []
    entities.extend(
        TesmartInputActiveBinarySensor(coordinator, entry, input_number)
        for input_number in range(1, input_count + 1)
    )
    entities.extend(
        TesmartOutputRoutedBinarySensor(coordinator, entry, output_number)
        for output_number in range(1, output_count + 1)
    )
    async_add_entities(entities)


class TesmartBaseBinarySensor(
    CoordinatorEntity[TesmartLanCoordinator], BinarySensorEntity
):
    """Base TESMart status binary sensor."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TesmartLanCoordinator, entry: ConfigEntry) -> None:
        """Initialize base binary sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="TESmart",
            name=entry.data[CONF_NAME],
            model="LAN Matrix",
        )


class TesmartInputActiveBinarySensor(TesmartBaseBinarySensor):
    """Status sensor showing whether an input is currently routed anywhere."""

    def __init__(
        self,
        coordinator: TesmartLanCoordinator,
        entry: ConfigEntry,
        input_number: int,
    ) -> None:
        """Initialize input status binary sensor."""
        super().__init__(coordinator, entry)
        self._input_number = input_number
        self._attr_name = f"Input {input_number} Active"
        self._attr_unique_id = f"{entry.entry_id}_input_{input_number}_active"
        self._attr_icon = "mdi:video-input-component"

    @property
    def is_on(self) -> bool:
        """True when at least one output is routed to this input."""
        data = self.coordinator.data or {}
        routes: dict[int, int] = data.get(DATA_ROUTES, {})
        return self._input_number in set(routes.values())


class TesmartOutputRoutedBinarySensor(TesmartBaseBinarySensor):
    """Status sensor showing whether an output currently has a route."""

    def __init__(
        self,
        coordinator: TesmartLanCoordinator,
        entry: ConfigEntry,
        output_number: int,
    ) -> None:
        """Initialize output status binary sensor."""
        super().__init__(coordinator, entry)
        self._output_number = output_number
        self._attr_name = f"Output {output_number} Routed"
        self._attr_unique_id = f"{entry.entry_id}_output_{output_number}_routed"
        self._attr_icon = "mdi:video-switch"

    @property
    def is_on(self) -> bool:
        """True when this output exists in the current route map."""
        data = self.coordinator.data or {}
        routes: dict[int, int] = data.get(DATA_ROUTES, {})
        return self._output_number in routes
