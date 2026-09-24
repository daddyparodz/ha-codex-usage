# Codex Usage for Home Assistant

Codex Usage is a custom Home Assistant integration distributed through HACS. It exposes Codex account usage, quota windows, reset times, credits, plan information, limit status, and banked resets as native Home Assistant entities.

## Features

- 5-hour usage and remaining quota
- Weekly usage and remaining quota
- Reset time sensors for both usage windows
- Plan, credits, and limit status sensors
- Banked reset tracking with grant and expiration details
- Calendar events for banked reset expirations and the next weekly reset
- ChatGPT device authorization
- Manual access-token configuration
- Configurable polling interval

## Installation

### HACS

1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Open the menu in the top-right corner and select **Custom repositories**.
4. Add:
   `https://github.com/daddyparodz/ha-codex-usage`
5. Select **Integration** as the category.
6. Install **Codex Usage**.
7. Restart Home Assistant.

## Configuration

After restarting Home Assistant:

1. Open **Settings** > **Devices & services**.
2. Select **Add integration**.
3. Search for **Codex Usage**.
4. Choose an authentication method.

### Sign in with ChatGPT

Select `device_code` to use the browser-based sign-in flow.

Home Assistant displays a ChatGPT sign-in URL and a one-time code, then monitors the authorization status. Setup completes automatically when the login is approved.

The resulting access token, refresh token, ID token, and account ID are stored in the config entry and used for subsequent updates.

### Access token

Select `access_token` to configure the integration with an existing access token.

The ChatGPT account ID can also be provided when required.

## Entities

| Entity | Name | Description |
| --- | --- | --- |
| `sensor.codex_5h_used` | 5h Used | Percentage used in the 5-hour window |
| `sensor.codex_5h_remaining` | 5h Remaining | Percentage remaining in the 5-hour window |
| `sensor.codex_5h_reset` | 5h Reset | Reset time for the 5-hour window |
| `sensor.codex_weekly_used` | Weekly Used | Percentage used in the weekly window |
| `sensor.codex_weekly_remaining` | Weekly Remaining | Percentage remaining in the weekly window |
| `sensor.codex_weekly_reset` | Weekly Reset | Reset time for the weekly window |
| `sensor.codex_credits` | Credits | Current credits balance |
| `sensor.codex_plan` | Plan | Current ChatGPT plan |
| `sensor.codex_limit_status` | Limit Status | Current rate-limit status |
| `sensor.codex_resets_available` | Banked Resets | Number of usable banked resets |
| `calendar.codex_reset_credits` | Banked Resets | Expiration events for usable banked resets |
| `calendar.codex_weekly_reset` | Weekly Reset | Next weekly usage-window reset |

## Banked resets

The **Banked Resets** sensor exposes additional information through state attributes, including:

- `banked_resets`
- `next_expiration`
- `banked_resets_last_update`
- `error`

Each banked reset includes its grant time, expiration time, current status, and remaining lifetime.

The **Banked Resets** calendar contains one event for each usable reset. Events begin at the reset expiration time and last one minute, providing a precise marker for when each reset expires.

Banked reset data is refreshed every minute.

## Weekly reset calendar

The **Weekly Reset** calendar exposes the next weekly usage-window reset reported by Codex. The event starts at the exact reset timestamp and lasts one minute.

The event updates with normal usage polling when Codex reports the next weekly reset.

## Options

The integration exposes an **Update interval** option for normal usage polling.

- Default: 30 seconds
- Minimum: 15 seconds
- Maximum: 3600 seconds

## Notes

- The integration uses ChatGPT and Codex endpoints that may change upstream.
- Authentication tokens are stored in the Home Assistant config entry and should be treated as sensitive credentials.
- Entity IDs and unique IDs are kept stable across updates.

## Disclaimer

Codex Usage is a community-maintained project and is not affiliated with or endorsed by OpenAI or Home Assistant.
