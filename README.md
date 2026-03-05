[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# TESMart LAN Matrix for Home Assistant

Custom Home Assistant integration for TESMart LAN matrix switches (TCP protocol).

## What this rebuild provides

- GUI setup through Home Assistant `Settings -> Devices & Services`
- GUI options editing after setup
- Supported hardware profiles: `8x16` and `16x16` only
- Easy multi-route control:
  - One `select` entity per output (`Output N Source`)
  - One global `select` entity for all outputs (`All Outputs Source`)
  - `Preset Slot` select (`1-8`)
  - `Mirror Outputs` button
  - `Load Preset` button
  - `Save Preset` button
- Device settings controls:
  - `Buzzer Enabled` (switch)
  - `Auto Input Detection` (switch)
  - `LED Timeout` (select: Off/10s/30s)
  - `Fan Mode` (select: Auto/Low/High, experimental mapping)
- Polling and route parsing that supports multi-digit ports (10-16)

## Install

### HACS (recommended)

1. Open HACS -> Integrations -> three-dot menu -> `Custom repositories`
2. Add this repository URL as category `Integration`
3. Install `TESMart LAN Matrix`
4. Restart Home Assistant

### Manual

1. Copy `custom_components/tesmart_matrix` into your HA config directory:
   `custom_components/tesmart_matrix`
2. Restart Home Assistant

## Configure (GUI)

1. Go to `Settings -> Devices & Services`
2. Click `Add Integration`
3. Search for `TESMart LAN Matrix`
4. Enter:
   - Name
   - Host/IP
   - Port (default `5000`)
   - Model (`8x16` or `16x16`)
   - Poll interval

After setup, use the generated `select` entities to route outputs.

## Services (all actions exposed)

The integration exposes domain services under `tesmart_matrix`:

- `set_route` (`input`, `output`, optional `entry_id`)
- `set_all_outputs` (`input`, optional `entry_id`)
- `mirror_outputs` (optional `entry_id`)
- `set_preset_slot` (`slot`, optional `entry_id`)
- `load_preset` (optional `slot`, optional `entry_id`)
- `save_preset` (optional `slot`, optional `entry_id`)
- `set_buzzer_enabled` (`enabled`, optional `entry_id`)
- `set_auto_input_detection` (`enabled`, optional `entry_id`)
- `set_led_timeout` (`timeout`: `Off|10s|30s`, optional `entry_id`)
- `set_fan_mode` (`mode`: `Auto|Low|High`, optional `entry_id`)

## Notes

- This integration targets TESMart matrix ASCII commands (e.g. `MT00SW..` / `MT00RD0000NT`).
- If your model only supports the older hex KVM command set, support can be added as a second protocol mode.
