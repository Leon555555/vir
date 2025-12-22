# app/__init__.py
from __future__ import annotations

import os
from flask import Flask
from app.extensions import db, login_manager


def create_app() -> Flask:
    app = Flask(__name__)

    # -------------------------
    # CONFIG
    # -------------------------
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # Render usa DATABASE_URL. SQLAlchemy prefiere postgresql+psycopg2
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if not db_url:
        # fallback local
        db_url = "sqlite:///local.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -------------------------
    # INIT EXTENSIONS
    # -------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # -------------------------
    # BLUEPRINTS
    # -------------------------
    from app.routes import main_bp, strava_bp  # <- IMPORTANTÍSIMO

    app.register_blueprint(main_bp)
    app.register_blueprint(strava_bp)

    # -------------------------
    # USER LOADER
    # -------------------------
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # -------------------------
    # DB AUTO CREATE (solo local)
    # -------------------------
    if os.getenv("AUTO_CREATE_DB", "0") == "1":
        with app.app_context():
            db.create_all()

    return app
