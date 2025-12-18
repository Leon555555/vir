# app/models_strava.py
from datetime import datetime
from app.extensions import db


class IntegrationAccount(db.Model):
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    provider = db.Column(db.String(50), nullable=False)  # "strava"

    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)
    scope = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class ExternalActivity(db.Model):
    __tablename__ = "external_activities"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # "strava"
    provider_activity_id = db.Column(db.String(100), nullable=False)

    name = db.Column(db.String(255))
    sport_type = db.Column(db.String(50))
    start_date = db.Column(db.DateTime)

    elapsed_time = db.Column(db.Integer)
    moving_time = db.Column(db.Integer)
    distance = db.Column(db.Float)
    total_elevation_gain = db.Column(db.Float)
    average_heartrate = db.Column(db.Float)

    raw_json = db.Column(db.JSON)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "provider", "provider_activity_id", name="uq_provider_activity"
        ),
    )
