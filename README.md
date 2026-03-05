
# Tesmart Home Assistant Integration

Custom Home Assistant integration for TESMart LAN matrix switches over TCP.

## Metadata

- Domain: `tesmart_matrix`
- Version: `1.5.0`
- IoT class: `local_polling`
- Config flow: enabled

## Maintainer

- Code owner: `@alexeinz`

## Features

- GUI setup from `Settings -> Devices & Services`
- GUI options flow for model and polling interval
- Supported models:
  - `8x16`
  - `16x16`
- Routing controls:
  - Per-output source selects (`Output N Source`)
  - Global source select (`All Outputs Source`)
  - Preset slot select (`1-8`)
  - `Mirror Outputs`, `Load Preset`, `Save Preset` buttons
- Device settings:
  - `Buzzer Enabled`
  - `Auto Input Detection`
  - `LED Timeout` (`Off` / `10s` / `30s`)
  - `Fan Mode` (`Auto` / `Low` / `High`, experimental)

## Installation

### HACS

1. Open `HACS -> Integrations -> Custom repositories`
2. Add this repository as category `Integration`
3. Install `Tesmart Home Assistant Integration`
4. Restart Home Assistant

### Manual

1. Copy `custom_components/tesmart_matrix` into your HA config directory
2. Restart Home Assistant

## Configuration

1. Go to `Settings -> Devices & Services`
2. Click `Add Integration`
3. Search for `Tesmart Home Assistant Integration`
4. Enter:
   - Name
   - Host/IP
   - Port (default `5000`)
   - Model (`8x16` or `16x16`)
   - Poll interval

## Services

Available under domain `tesmart_matrix`:

- `set_route` (`output`, `input`, optional `entry_id`)
- `set_all_outputs` (`input`, optional `entry_id`)
- `mirror_outputs` (optional `entry_id`)
- `set_preset_slot` (`slot`, optional `entry_id`)
- `load_preset` (optional `slot`, optional `entry_id`)
- `save_preset` (optional `slot`, optional `entry_id`)
- `set_buzzer_enabled` (`enabled`, optional `entry_id`)
- `set_auto_input_detection` (`enabled`, optional `entry_id`)
- `set_led_timeout` (`timeout`, optional `entry_id`)
- `set_fan_mode` (`mode`, optional `entry_id`)

## Notes

- Uses TESMart matrix ASCII commands (for example `MT00SW..` and `MT00RD0000NT`).
- Some models may return TCP responses in partial chunks; this integration handles chunked reads.
- If your device is hex-only KVM protocol, this integration may require protocol extension.

## Links

- Documentation: https://gitlab-jp.ispace-inc.com/ground/tesmart_control
- Issues: https://gitlab-jp.ispace-inc.com/ground/tesmart_control
