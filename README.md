# Codex Usage for Home Assistant

A custom Home Assistant integration (via HACS) that exposes your Codex usage as sensors.

## Features

- 5-hour usage and remaining percentage
- Weekly usage and remaining percentage
- Reset time sensors for both windows
- Plan, credits, and limit status sensors
- Browser-based ChatGPT login (device code)

## Authentication

Supported setup modes:

1. **Sign in with ChatGPT (recommended)**
- In the first step, keep `Authentication method = device_code`.
- Home Assistant shows:
  - a browser login URL
  - an OTP code
  - a required checkbox (`Browser login completed`)
- Open the URL, sign in, then return to Home Assistant.
- Tick the checkbox and press submit.
- Tokens are saved in the config entry and refreshed automatically.

2. **Paste access token manually**
- In the first step, select `Authentication method = access_token`.
- Paste token (optional account ID if needed) and submit.

## Installation (HACS)

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open menu (`⋮`) -> `Custom repositories`.
4. Add this repository URL.
5. Select category `Integration`.
6. Install **Codex Usage**.
7. Restart Home Assistant.

## Setup

1. Go to `Settings` -> `Devices & Services`.
2. Click `Add Integration`.
3. Search for **Codex Usage**.
4. Complete authentication.

If setup completed correctly, a `Codex Usage` config entry is created and sensors appear.

## Options

After setup, open integration options to change:
- `Update interval (seconds)`

## Entities created

- `sensor.codex_5h_used`
- `sensor.codex_5h_remaining`
- `sensor.codex_5h_reset`
- `sensor.codex_weekly_used`
- `sensor.codex_weekly_remaining`
- `sensor.codex_weekly_reset`
- `sensor.codex_credits`
- `sensor.codex_plan`
- `sensor.codex_limit_status`

## Notes

- This integration relies on internal endpoints and may require updates if upstream APIs change.
- Keep tokens private.

## Disclaimer

This project is community-maintained and is not an official OpenAI or Home Assistant integration.
