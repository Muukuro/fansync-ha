# FanSync BLE — Development Guidelines

This document captures build/config, testing, and development conventions specific to this repository to help advanced contributors work efficiently.

## 1) Build and Configuration
- Python: Project targets Python 3.13 (see Pipfile).
- Dependencies:
  - Home Assistant core is the only declared dependency for the library layer via Pipfile (homeassistant = "*"). At runtime the integration also relies on Bleak for BLE access; Bleak is provided by HA environments, but for standalone local dev you may need to `pip install bleak` or use Pipenv dev deps.
- Environment setup options:
  - Pipenv (preferred by repo):
    - Install Python 3.13.
    - `pipenv install --dev` (installs dev tools: pytest, bleak, ruff, black, etc.).
    - `pipenv shell` to enter the environment.
  - Plain venv:
    - `python3.13 -m venv .venv && source .venv/bin/activate`
    - `pip install homeassistant bleak pytest`
- Running Home Assistant for manual testing:
  - Put this repository folder under your HA config’s `custom_components/` as `custom_components/fansync_ble/`.
  - Start HA (Core or Container). For Core: `hass -c /path/to/config`.
  - Add the integration via Settings → Devices & Services → Add Integration → FanSync BLE.
- BLE requirements and OS specifics:
  - Linux: user must have permission to access Bluetooth (bluetooth group, or run HA with proper capabilities). BlueZ is required. For Docker, grant `--net=host --privileged` or use Bluetooth Proxy.
  - macOS: CoreBluetooth is supported by Bleak; ensure Bluetooth is enabled and HA/Core has access.
  - Windows: Bleak uses WinRT; ensure BT driver is functional.
  - If local BT is not available in your HA runtime, use ESPHome Bluetooth Proxy.
- Integration behavior constraints:
  - BLE sessions must be short-lived: connect → GET → CONTROL if needed → disconnect, with a small post-disconnect delay.
  - Always preserve untouched fields when emitting CONTROL frames.

## 2) Testing
- What we can test without HA:
  - Frame construction and checksum math in `custom_components/fansync_ble/client.py`.
  - Parsing of RETURN frames via `FanState.from_bytes`.
- Quick local test (non-HA):
  - Run `pytest -q`.
  - Or use a temp script for checksum verification, see README for an example.

## 3) CI
- GitHub Actions run:
  - Lint (Ruff), format check (Black)
  - Unit tests (pytest)
  - CodeQL security analysis

## 4) Contribution tips
- Use Pipenv for a smooth setup: `pipenv install --dev && pipenv shell`.
- Run `ruff check .` and `black --check .` before committing.
- Keep protocol helpers small and pure where possible to make them unit-testable without HA.

## 5) Cleanup Policy for Tests
- Any temporary local test files (e.g., `tmp_test_checksum.py`) are for local verification only and should not be committed.