"""Data coordinator for Codex Usage."""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .auth_device import account_id_from_id_token
from .const import (
    CLIENT_ID,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_AUTH_METHOD,
    CONF_BACKEND_URL,
    CONF_CODEX_HOME,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_BACKEND_URL,
    DEFAULT_CODEX_HOME,
    DEFAULT_REFRESH_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _format_reset_time(epoch_seconds: int | None, include_date: bool) -> str | None:
    if not epoch_seconds:
        return None

    dt = datetime.fromtimestamp(int(epoch_seconds), tz=UTC).astimezone()
    time_txt = dt.strftime("%H:%M")
    if not include_date:
        return time_txt
    return f"{dt.strftime('%d/%m')} - {time_txt}"


def _jwt_expired(token: str, skew_seconds: int = 120) -> bool:
    parts = token.split(".")
    if len(parts) < 2:
        return False

    try:
        payload_raw = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_raw.encode()).decode())
    except Exception:
        return False

    exp = payload.get("exp")
    if not exp:
        return False

    return int(exp) <= int(datetime.now(tz=UTC).timestamp()) + skew_seconds


class CodexUsageCoordinator(DataUpdateCoordinator[dict]):
    """Fetch Codex usage data and expose normalized values."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._cfg = entry.data

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=int(self._cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
            ),
        )

    async def _async_read_auth_json(self, codex_home: str) -> tuple[Path, dict]:
        auth_path = Path(codex_home).expanduser() / "auth.json"

        def _read() -> dict:
            with auth_path.open("r", encoding="utf-8") as f:
                return json.load(f)

        auth = await self.hass.async_add_executor_job(_read)
        return auth_path, auth

    async def _async_write_auth_json(self, auth_path: Path, payload: dict) -> None:
        def _write() -> None:
            auth_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        await self.hass.async_add_executor_job(_write)

    async def _async_refresh_token(self, refresh_token: str, refresh_url: str) -> dict:
        payload = {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.post(refresh_url, json=payload, timeout=30) as resp:
                raw = await resp.text()
                if resp.status >= 400:
                    raise UpdateFailed(f"Token refresh failed: HTTP {resp.status} {raw}")
                return json.loads(raw)
        except ClientError as err:
            raise UpdateFailed(f"Token refresh failed: {err}") from err

    async def _async_maybe_refresh_embedded_tokens(
        self, access_token: str, refresh_token: str, account_id: str | None
    ) -> tuple[str, str | None]:
        if not access_token or not refresh_token or not _jwt_expired(access_token):
            return access_token, account_id

        refreshed = await self._async_refresh_token(
            refresh_token, self._cfg.get(CONF_REFRESH_URL, DEFAULT_REFRESH_URL)
        )

        new_access = refreshed.get("access_token") or access_token
        new_refresh = refreshed.get("refresh_token") or refresh_token
        new_id_token = refreshed.get("id_token") or self._cfg.get(CONF_ID_TOKEN, "")
        new_account_id = account_id_from_id_token(new_id_token) or account_id

        new_data = dict(self.entry.data)
        new_data[CONF_ACCESS_TOKEN] = new_access
        new_data[CONF_REFRESH_TOKEN] = new_refresh
        new_data[CONF_ID_TOKEN] = new_id_token
        new_data[CONF_ACCOUNT_ID] = new_account_id or ""
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)
        self._cfg = self.entry.data

        return new_access, new_account_id

    async def _async_get_bearer(self) -> tuple[str, str | None]:
        access_token = (self._cfg.get(CONF_ACCESS_TOKEN) or "").strip()
        refresh_token = (self._cfg.get(CONF_REFRESH_TOKEN) or "").strip()
        account_id = (self._cfg.get(CONF_ACCOUNT_ID) or "").strip() or None

        if access_token:
            return await self._async_maybe_refresh_embedded_tokens(
                access_token, refresh_token, account_id
            )

        codex_home = self._cfg.get(CONF_CODEX_HOME, DEFAULT_CODEX_HOME)
        try:
            auth_path, auth = await self._async_read_auth_json(codex_home)
        except Exception as err:
            raise UpdateFailed(f"Cannot read {codex_home}/auth.json: {err}") from err

        token = (auth.get("tokens") or {}).get("access_token")
        refresh = (auth.get("tokens") or {}).get("refresh_token")
        file_account_id = (auth.get("tokens") or {}).get("account_id")
        if not token:
            raise UpdateFailed("auth.json does not contain tokens.access_token")

        if _jwt_expired(token):
            if not refresh:
                raise UpdateFailed("Codex token expired and no refresh_token was found")

            refreshed = await self._async_refresh_token(
                refresh, self._cfg.get(CONF_REFRESH_URL, DEFAULT_REFRESH_URL)
            )
            auth.setdefault("tokens", {})
            if refreshed.get("access_token"):
                auth["tokens"]["access_token"] = refreshed["access_token"]
                token = refreshed["access_token"]
            if refreshed.get("refresh_token"):
                auth["tokens"]["refresh_token"] = refreshed["refresh_token"]
            auth["last_refresh"] = datetime.now(tz=UTC).isoformat()
            await self._async_write_auth_json(auth_path, auth)

        return token, file_account_id or account_id

    async def _async_update_data(self) -> dict:
        token, account_id = await self._async_get_bearer()
        backend_url = self._cfg.get(CONF_BACKEND_URL, DEFAULT_BACKEND_URL)

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "codex-usage-ha-integration",
        }
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id

        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(backend_url, headers=headers, timeout=30) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise UpdateFailed(
                        f"Codex usage request failed: HTTP {resp.status} {body}"
                    )
                raw = await resp.json()
        except ClientError as err:
            raise UpdateFailed(f"Network error: {err}") from err

        rate = raw.get("rate_limit") or raw.get("rateLimits") or {}
        primary = rate.get("primary_window") or rate.get("primary") or {}
        secondary = rate.get("secondary_window") or rate.get("secondary") or {}

        p_used = float(primary.get("used_percent", 0))
        s_used = float(secondary.get("used_percent", 0))

        return {
            "plan": raw.get("plan_type") or raw.get("planType"),
            "primary_used_percent": p_used,
            "primary_remaining_percent": max(0.0, 100.0 - p_used),
            "primary_reset_time": _format_reset_time(
                primary.get("reset_at"), include_date=False
            ),
            "secondary_used_percent": s_used,
            "secondary_remaining_percent": max(0.0, 100.0 - s_used),
            "secondary_reset_time": _format_reset_time(
                secondary.get("reset_at"), include_date=True
            ),
            "credits_balance": (raw.get("credits") or {}).get("balance"),
            "rate_limit_reached_type": (
                (raw.get("rate_limit_reached_type") or {}).get("kind")
                if isinstance(raw.get("rate_limit_reached_type"), dict)
                else raw.get("rate_limit_reached_type")
            )
            or "OK",
            "last_update": datetime.now(tz=UTC).isoformat(),
        }
