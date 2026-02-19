# FanSync BLE - Home Assistant Integration
[![Tests](https://github.com/Muukuro/fansync-ha/actions/workflows/test.yml/badge.svg)](https://github.com/Muukuro/fansync-ha/actions/workflows/test.yml)
[![HACS](https://github.com/Muukuro/fansync-ha/actions/workflows/hacs.yml/badge.svg)](https://github.com/Muukuro/fansync-ha/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/Muukuro/fansync-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Muukuro/fansync-ha/actions/workflows/hassfest.yml)
[![Latest Release](https://img.shields.io/github/v/release/Muukuro/fansync-ha?sort=semver)](https://github.com/Muukuro/fansync-ha/releases)
[![License](https://img.shields.io/github/license/Muukuro/fansync-ha)](LICENSE)

Control FanSync Bluetooth ceiling fans from Home Assistant.

This is an unofficial Home Assistant custom integration for Fanimation FanSync Bluetooth controls:
https://fanimation.com/product-category/controls-remotes/fansync/fansync-bluetooth/

This repository provides a custom integration that uses a reverse-engineered BLE protocol and short-lived BLE sessions for reliability.

What you get:
- Fan control (`off`, `low`, `medium`, `high`)
- Optional light control (dimmable or on/off)
- Optional direction control

## Install in Home Assistant
1. Copy this repository to your HA config at `custom_components/fansync_ble/`.
2. Restart Home Assistant.
3. Go to `Settings -> Devices & Services -> Add Integration -> FanSync BLE`.
4. Let it scan, select your device, and save.

Created entities:
- Always: Fan entity (off/low/medium/high, optional direction)
- Optional: Light entity (dimmable or on/off based on options)

## Configuration Options
- `has_light`: when false, no light entity is created.
- `dimmable`: when false, light behaves as on/off and writes are clamped to `0/100`.
- `direction_supported`: enables direction control.
- `poll_interval`: coordinator polling interval in seconds.

## Development
Pipenv is preferred.

- Python: 3.13
- Runtime note: Home Assistant typically provides BLE stack dependencies in production.

```bash
pipenv install --dev
pipenv run ruff check .
pipenv run black --check .
pipenv run pytest -q
```

### Option B: Plain venv
- Create venv: `python3.13 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install homeassistant bleak pytest ruff black`
- Run tests: `pytest -q`

## BLE and Platform Notes
- Linux: Ensure BlueZ and Bluetooth permissions. In Docker, grant `--net=host --privileged` or use ESPHome Bluetooth Proxy.
- macOS: CoreBluetooth is supported by Bleak; ensure Bluetooth is enabled and HA/Core has access.
- Windows: Bleak uses WinRT; ensure BT drivers are functional.

## Protocol Summary
- Fixed 10-byte frame with checksum.
- Commands: `GET=0x30`, `CONTROL=0x31`, `RETURN=0x32`.
- Speeds: `0=off`, `1=low`, `2=medium`, `3=high`.
- Control writes preserve unchanged fields from last known state.
- BLE sessions are short-lived: connect -> read/write -> disconnect.

## CI
- GitHub Actions run linting (Ruff, Black), tests (pytest), and CodeQL.
- HACS validation and Hassfest validation are included.

## Community and Contribution
- Contributing guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security policy: `SECURITY.md`
- Support guide: `SUPPORT.md`

## HACS Submission Checklist
- `hacs.json` present and valid.
- `manifest.json` version bumped for release.
- HACS Action passes without brand ignores.
- Hassfest passes.
- Integration icon/brand assets published in `home-assistant/brands`.
- Create a GitHub Release for the submitted version.
