# app/integrations/strava_sync.py
from __future__ import annotations

from datetime import datetime
from app.extensions import db
from app.models_strava import ExternalActivity
from app.integrations.strava_client import get_strava_client


def _parse_dt(s: str | None):
    if not s:
        return None
    # Strava suele dar: "2025-12-18T16:08:00Z"
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def sync_latest_activities(user_id: int, per_page: int = 30) -> int:
    client = get_strava_client(user_id)
    activities = client.list_activities(per_page=per_page, page=1)

    saved = 0

    for a in activities:
        activity_id = str(a.get("id"))
        if not activity_id:
            continue

        row = ExternalActivity.query.filter_by(
            user_id=user_id,
            provider="strava",
            provider_activity_id=activity_id
        ).first()

        if not row:
            row = ExternalActivity(
                user_id=user_id,
                provider="strava",
                provider_activity_id=activity_id
            )
            db.session.add(row)
            saved += 1

        row.name = a.get("name")
        row.sport_type = a.get("sport_type") or a.get("type")
        row.distance_m = a.get("distance")
        row.moving_time_s = a.get("moving_time")
        row.elapsed_time_s = a.get("elapsed_time")
        row.start_date_utc = _parse_dt(a.get("start_date"))
        row.raw_json = a

    db.session.commit()
    return saved
