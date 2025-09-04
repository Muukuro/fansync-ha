# FanSync BLE
Control a FanSync BLE ceiling fan (fan + light) using a reverse‑engineered protocol.

## Install
1. Copy this folder to your Home Assistant `/config/custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **FanSync BLE**.
4. Let it scan once, select your fan, save. You’ll get a Fan entity and (optionally) a Light entity.

## Options
- **Has light**: If disabled, no Light entity is created.
- **Dimmable**: When off, the light behaves as on/off and the integration clamps writes to 0/100.
- **Direction supported**: Enables a direction toggle on the Fan entity (forward/reverse).
- **Poll interval**: Seconds between state polls.

## Notes
- Speeds: 0=off, 1=low, 2=medium, 3=high.
- The integration sends GET and listens for RETURN, then writes CONTROL frames preserving other fields.
- Works with HA OS/Supervised/Container/Core. For Docker without local BT, use an ESPHome Bluetooth Proxy.
