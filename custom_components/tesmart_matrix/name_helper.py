"""Helpers for user-defined TESMart input and output names."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .const import CONF_INPUT_NAMES, CONF_OUTPUT_NAMES


def _get_name(mapping: dict[str, str], number: int, prefix: str) -> str:
    """Return a configured name or the default numbered label."""
    return mapping.get(str(number), f"{prefix} {number}")


def get_input_name(entry: ConfigEntry, input_number: int) -> str:
    """Get the configured label for an input."""
    input_names = entry.options.get(CONF_INPUT_NAMES, {})
    return _get_name(input_names, input_number, "Input")


def get_output_name(entry: ConfigEntry, output_number: int) -> str:
    """Get the configured label for an output."""
    output_names = entry.options.get(CONF_OUTPUT_NAMES, {})
    return _get_name(output_names, output_number, "Output")
