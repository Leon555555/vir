# app/integrations/strava_sync.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from app.extensions import db
from app.models_strava import IntegrationAccount, ExternalActivity
from app.integrations.strava_client import get_strava_client, token_is_expired


def _parse_strava_datetime(iso_str: str | None) -> datetime | None:
    """
    Convierte fechas ISO de Strava a datetime naive UTC
    """
    if not iso_str:
        return None
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _ensure_valid_token(account: IntegrationAccount) -> IntegrationAccount:
    """
    Refresca el token si está vencido
    """
    client = get_strava_client()

    if token_is_expired(account.expires_at):
        data = client.refresh_access_token(account.refresh_token)

        account.access_token = data["access_token"]
        account.refresh_token = data["refresh_token"]
        account.expires_at = data["expires_at"]
        account.scope = data.get("scope")

        db.session.commit()

    return account


def sync_latest_activities(
    user_id: int,
    per_page: int = 50,
    max_pages: int = 3
) -> Dict:
    """
    Descarga las últimas actividades del atleta desde Strava
    y las guarda en external_activities
    """

    account = IntegrationAccount.query.filter_by(
        user_id=user_id,
        provider="strava"
    ).first()

    if not account:
        return {"ok": False, "error": "Usuario sin Strava conectado"}

    account = _ensure_valid_token(account)
    client = get_strava_client()

    created = 0
    updated = 0

    for page in range(1, max_pages + 1):
        activities = client.get(
            "/athlete/activities",
            account.access_token,
            params={
                "page": page,
                "per_page": per_page
            }
        )

        if not activities:
            break

        for a in activities:
            activity_id = str(a.get("id"))
            if not activity_id:
                continue

            row = ExternalActivity.query.filter_by(
                user_id=user_id,
                provider="strava",
                provider_activity_id=activity_id
            ).first()

            if row is None:
                row = ExternalActivity(
                    user_id=user_id,
                    provider="strava",
                    provider_activity_id=activity_id
                )
                db.session.add(row)
                created += 1
            else:
                updated += 1

            # Mapeo de campos principales
            row.name = a.get("name")
            row.sport_type = a.get("sport_type") or a.get("type")
            row.start_date = _parse_strava_datetime(a.get("start_date"))
            row.elapsed_time = a.get("elapsed_time")
            row.moving_time = a.get("moving_time")
            row.distance = a.get("distance")
            row.total_elevation_gain = a.get("total_elevation_gain")
            row.average_heartrate = a.get("average_heartrate")
            row.raw_json = a

        db.session.commit()

    return {
        "ok": True,
        "created": created,
        "updated": updated
    }
