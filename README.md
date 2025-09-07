# FanSync BLE
Control a FanSync BLE ceiling fan (fan + light) using a reverse‑engineered protocol.

## Install in Home Assistant
1. Copy this repository folder under your HA config’s `custom_components/` as `custom_components/fansync_ble/`.
2. Restart Home Assistant.
3. In HA: Settings → Devices & Services → Add Integration → FanSync BLE.
4. Let it scan once, select your fan, save. You’ll get a Fan entity and (optionally) a Light entity.

## Development environment
We support two setups. Pipenv is preferred for contributors.

- Python: 3.13
- Runtime deps: Home Assistant provides Bleak in typical HA installs. For local dev and tests, we list Bleak as a dev dependency.

### Option A: Pipenv (preferred)
- Install Python 3.13.
- Run:
  - `pipenv install --dev`
  - `pipenv shell`
- Run tests: `pytest -q`
- Lint/format checks: `ruff check .` and `black --check .`

### Option B: Plain venv
- Create venv: `python3.13 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install homeassistant bleak pytest`
- Run tests: `pytest -q`

### BLE and OS specifics
- Linux: Ensure BlueZ and Bluetooth permissions. In Docker, grant `--net=host --privileged` or use ESPHome Bluetooth Proxy.
- macOS: CoreBluetooth is supported by Bleak; ensure Bluetooth is enabled and HA/Core has access.
- Windows: Bleak uses WinRT; ensure BT drivers are functional.

### What the tests cover
- Protocol helpers in `custom_components/fansync_ble/client.py` (frame construction, checksum, parsing). No HA instance required.

## CI
- GitHub Actions run linting (Ruff, Black), tests (pytest), and CodeQL.

## Options
- **Has light**: If disabled, no Light entity is created.
- **Dimmable**: When off, the light behaves as on/off and the integration clamps writes to 0/100.
- **Direction supported**: Enables a direction toggle on the Fan entity (forward/reverse).
- **Poll interval**: Seconds between state polls.

## Notes
- Speeds: 0=off, 1=low, 2=medium, 3=high.
- BLE sessions are short-lived: connect → GET/CONTROL → disconnect, preserving untouched fields.
- Works with HA OS/Supervised/Container/Core. For Docker without local BT, use an ESPHome Bluetooth Proxy.
