# app/integrations/strava_client.py
from __future__ import annotations

import os
import time
import requests

from app.extensions import db
from app.models_strava import IntegrationAccount


STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


def _client_id() -> str:
    return os.getenv("STRAVA_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("STRAVA_CLIENT_SECRET", "").strip()


def _redirect_uri() -> str:
    return os.getenv("STRAVA_REDIRECT_URI", "").strip()


def build_authorize_url(state: str) -> str:
    # scope típico para leer actividades
    scope = "read,activity:read_all"
    return (
        f"{STRAVA_AUTH_URL}"
        f"?client_id={_client_id()}"
        f"&response_type=code"
        f"&redirect_uri={_redirect_uri()}"
        f"&approval_prompt=auto"
        f"&scope={scope}"
        f"&state={state}"
    )


def exchange_code_for_token(code: str) -> dict:
    payload = {
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "code": code,
        "grant_type": "authorization_code",
    }
    r = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def refresh_access_token(refresh_token: str) -> dict:
    payload = {
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    r = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def get_valid_access_token(user_id: int) -> str:
    acc = IntegrationAccount.query.filter_by(user_id=user_id, provider="strava").first()
    if not acc:
        raise RuntimeError("El usuario no tiene Strava conectado.")

    now = int(time.time())
    # refrescar si expira en <= 60s
    if acc.expires_at <= now + 60:
        data = refresh_access_token(acc.refresh_token)
        acc.access_token = data["access_token"]
        acc.refresh_token = data["refresh_token"]
        acc.expires_at = int(data["expires_at"])
        # athlete.id puede venir en algunos responses
        athlete = data.get("athlete") or {}
        if athlete.get("id"):
            acc.external_user_id = str(athlete["id"])
        db.session.commit()

    return acc.access_token


def api_get(path: str, access_token: str, params: dict | None = None) -> dict | list:
    url = f"{STRAVA_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def get_strava_client(user_id: int):
    """
    Helper simple para que tu código haga:
    client = get_strava_client(user_id)
    client.list_activities(...)
    """
    return StravaClient(user_id)


class StravaClient:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def access_token(self) -> str:
        return get_valid_access_token(self.user_id)

    def list_activities(self, per_page: int = 30, page: int = 1):
        token = self.access_token()
        return api_get("/athlete/activities", token, params={"per_page": per_page, "page": page})
