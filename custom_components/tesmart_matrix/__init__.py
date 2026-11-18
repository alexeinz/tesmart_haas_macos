"""TESMart LAN integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .coordinator import TesmartLanCoordinator

PLATFORMS: list[Platform] = [
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
]
_ENTRY_ID = "entry_id"

SERVICE_SET_ROUTE = "set_route"
SERVICE_SET_ALL_OUTPUTS = "set_all_outputs"
SERVICE_MIRROR_OUTPUTS = "mirror_outputs"
SERVICE_SET_PRESET_SLOT = "set_preset_slot"
SERVICE_LOAD_PRESET = "load_preset"
SERVICE_SAVE_PRESET = "save_preset"
SERVICE_SET_BUZZER_ENABLED = "set_buzzer_enabled"
SERVICE_SET_AUTO_INPUT_DETECTION = "set_auto_input_detection"
SERVICE_SET_LED_TIMEOUT = "set_led_timeout"
SERVICE_SET_FAN_MODE = "set_fan_mode"

_ALL_SERVICES = (
    SERVICE_SET_ROUTE,
    SERVICE_SET_ALL_OUTPUTS,
    SERVICE_MIRROR_OUTPUTS,
    SERVICE_SET_PRESET_SLOT,
    SERVICE_LOAD_PRESET,
    SERVICE_SAVE_PRESET,
    SERVICE_SET_BUZZER_ENABLED,
    SERVICE_SET_AUTO_INPUT_DETECTION,
    SERVICE_SET_LED_TIMEOUT,
    SERVICE_SET_FAN_MODE,
)

SERVICE_SCHEMA_ROUTE = vol.Schema(
    {
        vol.Optional(_ENTRY_ID): cv.string,
        vol.Required("output"): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
        vol.Required("input"): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
    }
)
SERVICE_SCHEMA_ALL_OUTPUTS = vol.Schema(
    {
        vol.Optional(_ENTRY_ID): cv.string,
        vol.Required("input"): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
    }
)
SERVICE_SCHEMA_PRESET_SLOT = vol.Schema(
    {
        vol.Optional(_ENTRY_ID): cv.string,
        vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
    }
)
SERVICE_SCHEMA_TOGGLE = vol.Schema(
    {
        vol.Optional(_ENTRY_ID): cv.string,
        vol.Required("enabled"): cv.boolean,
    }
)
SERVICE_SCHEMA_LED_TIMEOUT = vol.Schema(
    {
        vol.Optional(_ENTRY_ID): cv.string,
        vol.Required("timeout"): vol.In(["Off", "10s", "30s"]),
    }
)
SERVICE_SCHEMA_FAN_MODE = vol.Schema(
    {
        vol.Optional(_ENTRY_ID): cv.string,
        vol.Required("mode"): vol.In(["Auto", "Low", "High"]),
    }
)
SERVICE_SCHEMA_ENTRY_ONLY = vol.Schema({vol.Optional(_ENTRY_ID): cv.string})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TESMart from a config entry."""
    coordinator = TesmartLanCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    if not hass.services.has_service(DOMAIN, SERVICE_SET_ROUTE):
        _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            for service in _ALL_SERVICES:
                hass.services.async_remove(DOMAIN, service)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


def _get_coordinator(hass: HomeAssistant, entry_id: str | None) -> TesmartLanCoordinator:
    """Resolve target coordinator from entry ID or single loaded entry."""
    domain_data = hass.data.get(DOMAIN, {})
    coordinators = {
        key: value
        for key, value in domain_data.items()
        if isinstance(value, TesmartLanCoordinator)
    }
    if not coordinators:
        raise ServiceValidationError("No TESMart entries are currently loaded.")

    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise ServiceValidationError(f"Unknown TESMart entry_id '{entry_id}'.")
        return coordinator

    if len(coordinators) == 1:
        return next(iter(coordinators.values()))

    raise ServiceValidationError("Multiple TESMart entries loaded; provide 'entry_id'.")


def _register_services(hass: HomeAssistant) -> None:
    """Register TESMart domain services."""

    async def async_set_route(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_route(
            output=int(call.data["output"]),
            input_port=int(call.data["input"]),
        )

    async def async_set_all_outputs(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_all_outputs(input_port=int(call.data["input"]))

    async def async_mirror_outputs(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_mirror_outputs()

    async def async_set_preset_slot(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_preset_slot(str(call.data["slot"]))

    async def async_load_preset(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        slot = call.data.get("slot")
        await coordinator.async_load_preset(int(slot) if slot is not None else None)

    async def async_save_preset(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        slot = call.data.get("slot")
        await coordinator.async_save_preset(int(slot) if slot is not None else None)

    async def async_set_buzzer_enabled(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_buzzer_enabled(bool(call.data["enabled"]))

    async def async_set_auto_input_detection(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_auto_input_detection(bool(call.data["enabled"]))

    async def async_set_led_timeout(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_led_timeout(str(call.data["timeout"]))

    async def async_set_fan_mode(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(_ENTRY_ID))
        await coordinator.async_set_fan_mode(str(call.data["mode"]))

    hass.services.async_register(
        DOMAIN, SERVICE_SET_ROUTE, async_set_route, schema=SERVICE_SCHEMA_ROUTE
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALL_OUTPUTS,
        async_set_all_outputs,
        schema=SERVICE_SCHEMA_ALL_OUTPUTS,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MIRROR_OUTPUTS,
        async_mirror_outputs,
        schema=SERVICE_SCHEMA_ENTRY_ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PRESET_SLOT,
        async_set_preset_slot,
        schema=SERVICE_SCHEMA_PRESET_SLOT,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOAD_PRESET,
        async_load_preset,
        schema=vol.Schema(
            {
                vol.Optional(_ENTRY_ID): cv.string,
                vol.Optional("slot"): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_PRESET,
        async_save_preset,
        schema=vol.Schema(
            {
                vol.Optional(_ENTRY_ID): cv.string,
                vol.Optional("slot"): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BUZZER_ENABLED,
        async_set_buzzer_enabled,
        schema=SERVICE_SCHEMA_TOGGLE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AUTO_INPUT_DETECTION,
        async_set_auto_input_detection,
        schema=SERVICE_SCHEMA_TOGGLE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LED_TIMEOUT,
        async_set_led_timeout,
        schema=SERVICE_SCHEMA_LED_TIMEOUT,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_MODE,
        async_set_fan_mode,
        schema=SERVICE_SCHEMA_FAN_MODE,
    )
