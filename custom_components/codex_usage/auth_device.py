"""Codex ChatGPT device-code login helpers."""

from __future__ import annotations

import base64
import json
import re
from urllib.parse import urlencode

from aiohttp import ClientError
from homeassistant.helpers import aiohttp_client

from .const import AUTH_ISSUER, CLIENT_ID


def _claims_from_jwt(jwt_token: str) -> dict:
    try:
        payload = jwt_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return {}


def _compact_user_code(user_code: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", user_code or "").upper()


def account_id_from_id_token(id_token: str) -> str | None:
    claims = _claims_from_jwt(id_token)
    auth_claims = claims.get("https://api.openai.com/auth")
    if isinstance(auth_claims, dict):
        account_id = auth_claims.get("chatgpt_account_id")
        if isinstance(account_id, str) and account_id:
            return account_id
    return None


async def request_device_code(hass) -> dict:
    session = aiohttp_client.async_get_clientsession(hass)
    url = f"{AUTH_ISSUER}/api/accounts/deviceauth/usercode"
    payload = {"client_id": CLIENT_ID}

    try:
        async with session.post(url, json=payload, timeout=30) as resp:
            body = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"Device code request failed: HTTP {resp.status} {body}")
            data = json.loads(body)
    except ClientError as err:
        raise RuntimeError(f"Device code request failed: {err}") from err

    raw_code = data["user_code"]
    return {
        "device_auth_id": data["device_auth_id"],
        "user_code": raw_code,
        "user_code_compact": _compact_user_code(raw_code),
        "interval": int(data.get("interval", 5)),
        "verification_url": f"{AUTH_ISSUER}/codex/device",
    }


async def poll_device_code_once(hass, device_auth_id: str, user_code: str) -> dict | None:
    session = aiohttp_client.async_get_clientsession(hass)
    url = f"{AUTH_ISSUER}/api/accounts/deviceauth/token"
    payload = {
        "device_auth_id": device_auth_id,
        "user_code": user_code,
    }

    try:
        async with session.post(url, json=payload, timeout=30) as resp:
            if resp.status in (403, 404):
                return None
            body = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"Device auth failed: HTTP {resp.status} {body}")
            return json.loads(body)
    except ClientError as err:
        raise RuntimeError(f"Device auth failed: {err}") from err


async def exchange_code_for_tokens(hass, authorization_code: str, code_verifier: str) -> dict:
    session = aiohttp_client.async_get_clientsession(hass)
    url = f"{AUTH_ISSUER}/oauth/token"
    redirect_uri = f"{AUTH_ISSUER}/deviceauth/callback"

    body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": CLIENT_ID,
            "code_verifier": code_verifier,
        }
    )

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        async with session.post(url, data=body, headers=headers, timeout=30) as resp:
            raw = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"Token exchange failed: HTTP {resp.status} {raw}")
            data = json.loads(raw)
    except ClientError as err:
        raise RuntimeError(f"Token exchange failed: {err}") from err

    return {
        "id_token": data["id_token"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "account_id": account_id_from_id_token(data["id_token"]),
    }
