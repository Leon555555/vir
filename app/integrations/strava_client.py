# app/integrations/strava_client.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

STRAVA_WEB = "https://www.strava.com"
STRAVA_API = "https://www.strava.com/api/v3"


class StravaError(Exception):
    pass


def token_is_expired(expires_at: int, safety_seconds: int = 90) -> bool:
    return int(time.time()) >= int(expires_at) - safety_seconds


class StravaClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = str(client_id).strip()
        self.client_secret = str(client_secret).strip()

    def build_authorize_url(
        self,
        redirect_uri: str,
        state: str,
        scope: str = "read,activity:read_all",
        approval_prompt: str = "auto",
        response_type: str = "code",
    ) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": response_type,
            "redirect_uri": redirect_uri,
            "approval_prompt": approval_prompt,
            "scope": scope,
            "state": state,
        }
        return f"{STRAVA_WEB}/oauth/authorize?{urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        url = f"{STRAVA_WEB}/oauth/token"
        resp = requests.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=25,
        )
        if resp.status_code != 200:
            raise StravaError(f"Token exchange failed: {resp.status_code} {resp.text}")
        return resp.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        url = f"{STRAVA_WEB}/oauth/token"
        resp = requests.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=25,
        )
        if resp.status_code != 200:
            raise StravaError(f"Refresh failed: {resp.status_code} {resp.text}")
        return resp.json()

    def get(self, path: str, access_token: str, params: Optional[dict] = None) -> Any:
        url = f"{STRAVA_API}{path}"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params or {},
            timeout=25,
        )
        if resp.status_code != 200:
            raise StravaError(f"GET {path} failed: {resp.status_code} {resp.text}")
        return resp.json()


def get_strava_client() -> StravaClient:
    cid = os.getenv("STRAVA_CLIENT_ID", "").strip()
    csec = os.getenv("STRAVA_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        raise RuntimeError("Missing STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET in env vars.")
    return StravaClient(cid, csec)
