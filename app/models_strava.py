# app/models_strava.py
from __future__ import annotations

from datetime import datetime
from app.extensions import db


class IntegrationAccount(db.Model):
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)

    # Si tu tabla de usuarios se llama distinto, ajustamos esto después,
    # pero en la mayoría de proyectos es "user".
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, index=True)  # "strava"
    provider_user_id = db.Column(db.String(80), nullable=True, index=True)

    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)  # epoch seconds

    scope = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class ExternalActivity(db.Model):
    __tablename__ = "external_activities"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, index=True)  # "strava"
    provider_activity_id = db.Column(db.String(80), nullable=False, index=True)

    name = db.Column(db.String(255), nullable=True)
    sport_type = db.Column(db.String(80), nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)  # naive UTC
    elapsed_time = db.Column(db.Integer, nullable=True)
    moving_time = db.Column(db.Integer, nullable=True)
    distance = db.Column(db.Float, nullable=True)  # meters
    total_elevation_gain = db.Column(db.Float, nullable=True)
    average_heartrate = db.Column(db.Float, nullable=True)

    raw_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", "provider_activity_id", name="uq_user_provider_activity"),
    )
