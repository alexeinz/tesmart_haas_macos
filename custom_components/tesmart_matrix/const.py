"""Constants for TESMart LAN integration."""
from __future__ import annotations

from datetime import timedelta
from logging import Logger, getLogger

DOMAIN = "tesmart_matrix"
NAME = "TESMart LAN Matrix"

CONF_POLL_INTERVAL = "poll_interval"
CONF_MODEL = "model"
CONF_INPUT_NAMES = "input_names"
CONF_OUTPUT_NAMES = "output_names"

DEFAULT_PORT = 5000
DEFAULT_MODEL = "8x16"
DEFAULT_POLL_INTERVAL = 5

SUPPORTED_MODELS: dict[str, tuple[int, int]] = {
    "8x16": (8, 16),
    "16x16": (16, 16),
}

MIN_POLL_INTERVAL = 1
MAX_POLL_INTERVAL = 300

DATA_ROUTES = "routes"
DATA_AVAILABLE = "available"
DATA_SETTINGS = "settings"

SETTING_BUZZER_ENABLED = "buzzer_enabled"
SETTING_AUTO_INPUT_DETECTION = "auto_input_detection"
SETTING_LED_TIMEOUT = "led_timeout"
SETTING_FAN_MODE = "fan_mode"
SETTING_PRESET_SLOT = "preset_slot"

UPDATE_INTERVAL_FALLBACK = timedelta(seconds=DEFAULT_POLL_INTERVAL)

LOGGER: Logger = getLogger(__package__)
