# Codex Usage for Home Assistant

A custom Home Assistant integration (via HACS) that exposes your Codex usage as sensors.

## Features

- 5-hour usage and remaining percentage
- Weekly usage and remaining percentage
- Reset time sensors for both windows
- Plan, credits, and limit status sensors
- Browser-based ChatGPT login (device code), no manual token paste required

## Authentication

Recommended: **Sign in with ChatGPT (device code)**

- During setup, choose `Sign in with ChatGPT`.
- Home Assistant will show a URL and one-time code.
- Open the URL in any browser, sign in, enter the code, then confirm in Home Assistant.
- Tokens are saved in the config entry and refreshed automatically.

Other supported modes:

- `Use existing auth.json`
- `Paste access token manually`

## Installation (HACS)

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the menu (`⋮`) and select `Custom repositories`.
4. Add this repository URL.
5. Select category `Integration`.
6. Install **Codex Usage**.
7. Restart Home Assistant.

## Setup

1. Go to `Settings` -> `Devices & Services`.
2. Click `Add Integration`.
3. Search for **Codex Usage**.
4. Choose your auth method and finish setup.

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
