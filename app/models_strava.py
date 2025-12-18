# app/models_strava.py
from __future__ import annotations

from datetime import datetime
from app.extensions import db

# ============================================================
# STRAVA INTEGRATION MODELS
# ============================================================

class IntegrationAccount(db.Model):
    """
    Guarda tokens Strava por usuario.
    OJO: tu tabla de usuarios en app/models.py es __tablename__ = "user"
    así que el FK correcto es "user.id" (NO "users.id").
    """
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ FK correcto según tu models.py
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, default="strava")  # por si luego sumás Garmin, etc
    athlete_id = db.Column(db.BigInteger, nullable=True, index=True)

    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.BigInteger, nullable=True)

    scope = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_integration_user_provider"),
    )


class ExternalActivity(db.Model):
    """
    Cachea actividades traídas desde Strava, para no re-consultar siempre.
    """
    __tablename__ = "external_activities"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, default="strava")

    external_id = db.Column(db.BigInteger, nullable=False, index=True)  # id actividad en Strava
    name = db.Column(db.String(255), nullable=True)

    sport_type = db.Column(db.String(80), nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)

    distance_m = db.Column(db.Float, nullable=True)
    moving_time_s = db.Column(db.Integer, nullable=True)
    elapsed_time_s = db.Column(db.Integer, nullable=True)
    total_elevation_gain_m = db.Column(db.Float, nullable=True)

    raw_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("provider", "external_id", name="uq_external_activity_provider_externalid"),
    )


print("✅ models_strava importado (modelos Strava registrados).")
