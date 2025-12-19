# app/integrations/strava_client.py
from __future__ import annotations

import os
import time
import requests


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


def exchange_code_for_token(code: str) -> dict:
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Faltan STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }

    r = requests.post(STRAVA_TOKEN_URL, data=data, timeout=20)
    r.raise_for_status()
    return r.json()


def refresh_access_token(refresh_token: str) -> dict:
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Faltan STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    r = requests.post(STRAVA_TOKEN_URL, data=data, timeout=20)
    r.raise_for_status()
    return r.json()


def is_expired(expires_at: int) -> bool:
    # 60s de margen
    return int(expires_at) <= int(time.time()) + 60
