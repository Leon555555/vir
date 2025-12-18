# app/models_strava.py
from __future__ import annotations

from datetime import datetime
from app.extensions import db


class IntegrationAccount(db.Model):
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)

    # OJO: tu tabla de usuarios se llama "user" (no "users")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, default="strava", index=True)

    # Strava athlete id
    external_user_id = db.Column(db.String(64), nullable=True, index=True)

    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)  # unix timestamp

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_integration_user_provider"),
    )


class ExternalActivity(db.Model):
    __tablename__ = "external_activities"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, default="strava", index=True)

    # ✅ ESTA ES LA CLAVE QUE TE FALTABA (lo usa el sync)
    provider_activity_id = db.Column(db.String(64), nullable=False, index=True)

    name = db.Column(db.String(255), nullable=True)
    sport_type = db.Column(db.String(80), nullable=True)

    distance_m = db.Column(db.Float, nullable=True)
    moving_time_s = db.Column(db.Integer, nullable=True)
    elapsed_time_s = db.Column(db.Integer, nullable=True)

    start_date_utc = db.Column(db.DateTime, nullable=True)
    raw_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "provider", "provider_activity_id",
            name="uq_extact_user_provider_activity"
        ),
    )


print("✅ models_strava importado (modelos Strava registrados).")
