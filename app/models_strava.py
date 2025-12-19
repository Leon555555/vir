# app/models_strava.py
from __future__ import annotations

from datetime import datetime
from app.extensions import db


class IntegrationAccount(db.Model):
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, index=True)  # "strava"
    external_user_id = db.Column(db.String(80), nullable=True, index=True)

    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.Integer, nullable=True)  # epoch seconds

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_integration_user_provider"),
    )


class ExternalActivity(db.Model):
    __tablename__ = "external_activities"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, index=True)  # "strava"

    provider_activity_id = db.Column(db.String(80), nullable=False, index=True)

    name = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)

    distance_m = db.Column(db.Float, nullable=True)
    moving_time_s = db.Column(db.Integer, nullable=True)
    elapsed_time_s = db.Column(db.Integer, nullable=True)

    raw_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", "provider_activity_id", name="uq_external_activity"),
    )
