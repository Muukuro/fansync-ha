# AI Instructions — FanSync BLE Project

This document captures the **canonical context** for AI coding tools (e.g., Cursor/Copilot/ChatGPT) to continue work on this project without losing hard‑won insights.

## Scope and Goals
- Provide a Home Assistant custom integration that controls a **FanSync BLE** ceiling fan.
- Expose a **Fan** entity (3 speeds + off, optional direction) and an optional **Light** entity (dimmable or on/off).
- Keep **Bluetooth connections short**: connect → GET → CONTROL (if needed) → disconnect.
- Preserve **unchanged fields** when sending CONTROL frames.

## BLE Protocol (reverse‑engineered)
- Frames are **10 bytes**: `[0]=0x53, [1]=cmd, [2]=speed, [3]=direction, [4]=up, [5]=down, [6]=timerLo, [7]=timerHi, [8]=fanType, [9]=checksum(sum first 9 bytes & 0xFF)]`.
- Commands: `GET=0x30`, `CONTROL=0x31`, `RETURN=0x32`.
- Semantics used by the integration:
  - **speed**: 0=off, 1=low, 2=medium, 3=high.
  - **direction**: 0=forward, 1=reverse (only if hardware supports it).
  - **down**: 0–100 (if non‑dimmable, clamp to {0,100}).
  - **up**: reserved for a possible uplight (not implemented yet).
  - **timerLo/Hi**: preserved; not surfaced yet.
  - **fanType**: preserved as reported.
- The vendor app’s questionnaire (dimmable / reversible) **only affects UI behavior**; the frame **format is constant**.

## Integration Architecture
- **custom_components/fansync_ble** with: `config_flow.py`, `__init__.py`, `coordinator.py`, `client.py`, `fan.py`, `light.py`, `manifest.json`.
- **Config Flow** scans BLE once; stores the selected address as the **unique_id**. An **Options Flow** stores:
  - `has_light` (bool), `dimmable` (bool), `direction_supported` (bool), `poll_interval` (int seconds).
- **Coordinator** (DataUpdateCoordinator) polls `get_state()` every `poll_interval` seconds.
- **Client** wraps Bleak. Methods: `get_state()`, `set_speed()`, `set_light()`, `set_direction()`.
- **Entities** read `entry.options` to reflect UI: non‑dimmable lights expose `ColorMode.ONOFF` and clamp writes to 0/100; direction control appears only when enabled.
- Keep all writes **idempotent** by fetching state and re‑using preserved fields in CONTROL frames.

## Coding Conventions
- Prefer **async** APIs compatible with Home Assistant.
- Avoid long‑lived BLE connections; use retries sparingly and allow a short post‑disconnect delay.
- Strictly validate brightness percentages (0–100) and map HA percentages to 0/1/2/3 speeds.

## Roadmap Hints
- Add **Options Flow** for rescanning and re‑selecting the device.
- Add **timer** (Number entity) and **direction** button for quick toggle.
- Consider supporting **ESPHome Bluetooth Proxy** explicitly in docs.
- Prepare for **HACS**: repo at root of this folder, license, readme, tags, `hacs.json` and `manifest.json` with releases.
