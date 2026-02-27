# AGENTS.md - FanSync Bluetooth Project Instructions

This is the canonical AI agent instructions file for this repository.

## Purpose
- Build and maintain a Home Assistant custom integration for FanSync Bluetooth ceiling fans.
- Keep behavior stable with the reverse-engineered 10-byte protocol.
- Favor safe, minimal changes that preserve existing fan/light state fields.

## Repo Focus
- Integration code: `custom_components/fansync_ble/`
- Tests: `tests/`
- Community docs: `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`

## Protocol Guardrails (Do Not Break)
- Frame is always 10 bytes with checksum in byte 9.
- Commands: `GET=0x30`, `CONTROL=0x31`, `RETURN=0x32`.
- Speed mapping: `0=off`, `1=low`, `2=medium`, `3=high`.
- Preserve unchanged fields (`direction`, `up`, `down`, `timerLo`, `timerHi`, `fanType`) when sending control writes.
- BLE interaction style is short-lived: connect, read/write, disconnect.

## Product Behavior
- Fan entity is always present.
- Light entity is optional (`has_light` option).
- Non-dimmable light must clamp brightness writes to `0` or `100`.
- Direction controls only appear when `direction_supported` is enabled.
- Polling uses coordinator with configurable `poll_interval`.

## Coding Rules
- Use async patterns compatible with Home Assistant.
- Keep changes scoped; avoid broad refactors unless requested.
- Match current style and naming patterns in neighboring files.
- Add comments only when logic is not obvious.

## Community Doc Compliance
- Respect and follow repository policies in:
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
  - `SUPPORT.md`
- When changing contributor workflow, support process, or disclosure expectations, update these docs in the same PR.
- Do not direct security reports to public issues; always point to `SECURITY.md`.

## Validation Workflow
- Run targeted tests first, then full tests when possible:
  - `pipenv run pytest -q tests/test_client_protocol.py`
  - `pipenv run pytest -q`
- For lint checks (if tools are installed):
  - `pipenv run ruff check .`
  - `pipenv run black --check .`
- Before every commit, ensure `pipenv run black --check .` passes.

## Change Checklist
- Confirm option handling still works in config/options flow.
- Confirm fan percentage mapping still round-trips correctly.
- Confirm light behavior stays correct for dimmable and on/off modes.
- Confirm no protocol frame/checksum regressions in tests.

## Non-Goals Unless Requested
- Do not add new entities (timer, extra buttons, uplight support) unless asked.
- Do not change BLE transport strategy to persistent connections.
