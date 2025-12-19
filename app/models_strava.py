# app/models_strava.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class IntegrationAccount(db.Model):
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)

    # OJO: tu tabla users se llama "user"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, index=True)  # "strava"
    external_user_id = db.Column(db.String(64), nullable=True)       # athlete.id de Strava

    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class ExternalActivity(db.Model):
    __tablename__ = "external_activities"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, index=True)  # "strava"

    provider_activity_id = db.Column(db.String(64), nullable=False, index=True)

    name = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    start_date = db.Column(db.String(64), nullable=True)

    distance_m = db.Column(db.Float, nullable=True)
    moving_time_s = db.Column(db.Integer, nullable=True)
    elapsed_time_s = db.Column(db.Integer, nullable=True)

    raw = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", "provider_activity_id", name="uq_ext_act"),
    )


print("✅ models_strava importado (modelos Strava registrados).")
