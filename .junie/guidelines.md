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

## 6) Protocol Quick Reference (see AI_INSTRUCTIONS.md for full details)
- Frame format: 10 bytes — [0]=0x53, [1]=cmd, [2]=speed, [3]=direction, [4]=up, [5]=down, [6]=timerLo, [7]=timerHi, [8]=fanType, [9]=checksum(sum of first 9 bytes & 0xFF).
- Commands: GET=0x30, CONTROL=0x31, RETURN=0x32.
- Semantics in this integration:
  - speed: 0=off, 1=low, 2=medium, 3=high; map HA percentage to these steps.
  - direction: 0=forward, 1=reverse (only if hardware supports it via options).
  - down: 0–100 (dimmable); clamp to {0,100} if non‑dimmable.
  - up, timerLo/Hi, fanType: preserve values from the last valid state when sending CONTROL.
- Operational rules:
  - Keep BLE sessions short‑lived: connect → GET → CONTROL (if needed) → disconnect, then small delay.
  - Always preserve untouched fields when emitting CONTROL frames; if no valid prior state, use conservative assumptions (e.g., assume_light or assume_speed as in client methods).
- For the canonical, detailed protocol notes and rationale, read: AI_INSTRUCTIONS.md.