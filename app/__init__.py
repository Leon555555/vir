# app/__init__.py
from __future__ import annotations

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app.extensions import db

try:
    from flask_migrate import Migrate
except Exception:
    Migrate = None


login_manager = LoginManager()
login_manager.login_view = "main.login"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # -------------------------
    # Extensions
    # -------------------------
    db.init_app(app)
    login_manager.init_app(app)

    if Migrate is not None:
        Migrate(app, db)

    # -------------------------
    # User loader
    # -------------------------
    from app.models import User  # noqa

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # -------------------------
    # Blueprints (todos en routes.py)
    # -------------------------
    from app.routes import main_bp, strava_bp  # <- CLAVE: existen y exportan

    app.register_blueprint(main_bp)
    app.register_blueprint(strava_bp)

    # -------------------------
    # Contexto global para templates (admin_ok)
    # -------------------------
    from flask_login import current_user

    @app.context_processor
    def inject_admin_ok():
        admin_ok = False
        try:
            admin_ok = bool(
                getattr(current_user, "is_authenticated", False)
                and getattr(current_user, "is_admin", False)
            )
        except Exception:
            admin_ok = False
        return {"admin_ok": admin_ok}

    return app
