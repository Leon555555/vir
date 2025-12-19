# app/integrations/strava_sync.py
from __future__ import annotations

import requests
from datetime import datetime

from app.extensions import db
from app.models_strava import IntegrationAccount, ExternalActivity
from app.integrations.strava_client import refresh_access_token, is_expired

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


def _parse_start_date(v) -> datetime | None:
    if not v:
        return None
    # Strava suele venir como "2025-12-19T10:20:30Z"
    try:
        if isinstance(v, str) and v.endswith("Z"):
            v = v.replace("Z", "+00:00")
        return datetime.fromisoformat(v) if isinstance(v, str) else None
    except Exception:
        return None


def _ensure_valid_token(acc: IntegrationAccount) -> IntegrationAccount:
    if not acc.refresh_token:
        raise RuntimeError("No hay refresh_token guardado.")

    if acc.expires_at and not is_expired(acc.expires_at):
        return acc

    data = refresh_access_token(acc.refresh_token)

    acc.access_token = data.get("access_token")
    acc.refresh_token = data.get("refresh_token") or acc.refresh_token
    acc.expires_at = int(data.get("expires_at") or 0)
    acc.updated_at = datetime.utcnow()

    db.session.commit()
    return acc


def sync_latest_activities(user_id: int, per_page: int = 30) -> int:
    acc = IntegrationAccount.query.filter_by(user_id=user_id, provider="strava").first()
    if not acc:
        raise RuntimeError("Este usuario no tiene Strava vinculado.")

    acc = _ensure_valid_token(acc)

    headers = {"Authorization": f"Bearer {acc.access_token}"}
    params = {"per_page": per_page, "page": 1}

    r = requests.get(STRAVA_ACTIVITIES_URL, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    activities = r.json() or []

    inserted = 0

    for a in activities:
        activity_id = str(a.get("id"))
        if not activity_id:
            continue

        exists = ExternalActivity.query.filter_by(
            user_id=user_id,
            provider="strava",
            provider_activity_id=activity_id
        ).first()
        if exists:
            continue

        row = ExternalActivity(
            user_id=user_id,
            provider="strava",
            provider_activity_id=activity_id,
            name=a.get("name"),
            start_date=_parse_start_date(a.get("start_date")),
            distance_m=a.get("distance"),
            moving_time_s=a.get("moving_time"),
            elapsed_time_s=a.get("elapsed_time"),
            raw_json=a,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(row)
        inserted += 1

    db.session.commit()
    return inserted
