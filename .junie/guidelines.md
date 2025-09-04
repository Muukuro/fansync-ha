# FanSync BLE — Development Guidelines

This document captures build/config, testing, and development conventions specific to this repository to help advanced contributors work efficiently.

## 1) Build and Configuration
- Python: Project targets Python 3.13 (see Pipfile).
- Dependencies:
  - Home Assistant core is the only declared dependency for the library layer via Pipfile (homeassistant = "*"). At runtime the integration also relies on Bleak for BLE access; Bleak is provided by HA environments, but for standalone local dev you may need to `pip install bleak`.
- Environment setup options:
  - Pipenv (preferred by repo):
    - Install Python 3.13.
    - `pipenv install --dev` (installs Home Assistant).
    - `pipenv shell` to enter the environment.
  - Plain venv:
    - `python3.13 -m venv .venv && source .venv/bin/activate`
    - `pip install homeassistant bleak`
- Running Home Assistant for manual testing:
  - Put this repository folder under your HA config’s `custom_components/` as `custom_components/fansync_ble/`.
  - Start HA (Core or Container). For Core: `hass -c /path/to/config`.
  - Add the integration via Settings → Devices & Services → Add Integration → FanSync BLE.
- BLE requirements and OS specifics:
  - Linux: user must have permission to access Bluetooth (bluetooth group, or run HA with proper capabilities). BlueZ is required. For Docker, grant `--net=host --privileged` or use Bluetooth Proxy.
  - macOS: CoreBluetooth is supported by Bleak; ensure Bluetooth is enabled and HA/Core has access.
  - Windows: Bleak uses WinRT; ensure BT driver is functional.
  - If local BT is not available in your HA runtime, use ESPHome Bluetooth Proxy.
- Integration behavior constraints (important when modifying code):
  - BLE sessions must be short-lived: connect → GET → CONTROL if needed → disconnect, with a small post-disconnect delay.
  - Always preserve untouched fields when emitting CONTROL frames (see client.build_frame usage and FanState preservation).

## 2) Testing
Given this is a HA custom integration without an embedded test harness, tests are focused on import health and protocol helpers that can run outside HA.

- Quick local test prerequisites: use the venv/pipenv setup above.
- What we can test without HA:
  - Frame construction and checksum math in `custom_components/fansync_ble/client.py`.
  - Fan/light percentage mappings in `fan.py` and brightness scaling in `light.py` (pure functions can be imported; however, these files import HA symbols, so avoid importing the modules directly in a non-HA environment). For rapid checks, prefer testing the helpers in `client.py` that don’t import HA.

### Running a simple, non-HA test (verified)
- Create a temporary test file locally (do not commit) with the snippet below and run it with your active environment. It validates the 10-byte frame shape and checksum correctness against `build_frame`:

  Example script (save as `tmp_test_checksum.py`):

  ```text
  from custom_components.fansync_ble.client import build_frame
  from custom_components.fansync_ble.const import GET_FAN_STATUS, CONTROL_FAN_STATUS

  def checksum9(arr):
      return sum(arr[:9]) & 0xFF

  # 1) GET frame should preserve header 0x53 and produce correct checksum
  f_get = build_frame(GET_FAN_STATUS, 0,0,0,0,0,0,0)
  assert len(f_get) == 10 and f_get[0] == 0x53
  assert f_get[-1] == checksum9(f_get)

  # 2) CONTROL frame with typical state fields
  f_ctrl = build_frame(CONTROL_FAN_STATUS, 2, 1, 0, 75, 0x34, 0x12, 0x05)
  assert len(f_ctrl) == 10 and f_ctrl[1] == CONTROL_FAN_STATUS
  assert f_ctrl[-1] == checksum9(f_ctrl)

  print("OK: frames checksum validated")
  ```

- Run: `python tmp_test_checksum.py`
- Expected output: `OK: frames checksum validated`
- Remove the temporary file after use.

### Adding more tests
- For protocol-level tests, keep them independent from Home Assistant by testing only `custom_components.fansync_ble.client` helpers:
  - `FanState.from_bytes` parsing with crafted RETURN frames (`const.RETURN_FAN_STATUS`).
  - Speed and brightness clamping behavior when `st.valid` is False in `set_speed`/`set_light` (by calling `build_frame` directly or abstracting logic into new pure helpers if needed).
- For HA-integration tests, use Home Assistant’s pytest harness:
  - Create a dedicated tests package outside this repository or in a feature branch, install `pytest`, `pytest-asyncio`, and `homeassistant`, and follow HA custom integration test patterns (fixtures for `hass`, `mock_config_entry`, and patching Bleak with fakes).
  - Mock Bleak (`bleak.BleakClient` and `BleakScanner.discover`) to avoid real BLE.

## 3) Additional Development Information
- Protocol (from AI_INSTRUCTIONS.md):
  - 10-byte frames: [0]=0x53, [1]=cmd, [2]=speed(0..3), [3]=direction(0/1), [4]=up, [5]=down(0..100), [6]=timerLo, [7]=timerHi, [8]=fanType, [9]=checksum(sum first 9 & 0xFF).
  - Commands: GET=0x30, CONTROL=0x31, RETURN=0x32.
  - Preserve timer and fanType fields; UI-only flags (dimmable, direction) should not alter frame format.
- Architecture:
  - `config_flow.py` discovers BLE devices once and stores the MAC as unique_id.
  - `coordinator.py` polls using DataUpdateCoordinator at `poll_interval` seconds.
  - `client.py` wraps Bleak and implements `get_state`, `set_speed`, `set_light`, `set_direction`; ensures idempotent writes via preserved fields.
  - Entities (`fan.py`, `light.py`) reflect options flags and map HA abstractions to protocol fields.
- Async and connection hygiene:
  - Always use async HA APIs; avoid long-lived BLE sessions; include brief sleeps after writes and disconnects, as implemented.
  - Clamp brightness (0–100) and map fan speeds from HA percentages: 0, 33, 66, 100 thresholds as in `fan.py`.
- Code style and notes:
  - Prefer small, pure helpers for protocol math to allow unit testing without HA.
  - If you extend functionality (e.g., timer, uplight), maintain backward compatibility in frame layout and continue preserving unknown fields from the last known state.
  - Consider adding an options flow item for rescanning devices.
- Packaging for HACS:
  - Ensure `hacs.json`, `manifest.json`, README, license, and release tags are maintained for HACS consumption.

## 4) Troubleshooting tips
- Discovery returns no devices:
  - Increase timeout in `discover_candidates` or adjust `DEFAULT_NAME_HINT`.
  - Verify BLE permissions and that HA process sees the adapter.
- No RETURN after GET:
  - Some devices require enabling notifications first; `_ensure_notify` already attempts it before sending GET.
  - Consider retrying GET or handling timeouts via the coordinator if needed.
- Direction unsupported:
  - Keep `CONF_DIRECTION_SUPPORTED` False; the entity will hide direction controls.

## 5) Cleanup Policy for Tests
- Any temporary local test files (e.g., `tmp_test_checksum.py`) are for local verification only and should not be committed.
- After verifying, delete any such files. Only this `.junie/guidelines.md` should be added by this task.
