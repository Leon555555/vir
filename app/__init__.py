# app/__init__.py
from __future__ import annotations

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from app.config import Config
from app.extensions import db

login_manager = LoginManager()
login_manager.login_view = "main.login"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # -------------------------
    # EXTENSIONS
    # -------------------------
    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)

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
    # BLUEPRINTS (TODOS EN routes.py)
    # -------------------------
    from app.routes import main_bp, strava_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(strava_bp, url_prefix="/strava")

    # -------------------------
    # CONTEXTO GLOBAL
    # -------------------------
    from flask_login import current_user

    @app.context_processor
    def inject_admin_ok():
        return {
            "admin_ok": bool(
                getattr(current_user, "is_authenticated", False)
                and getattr(current_user, "is_admin", False)
            )
        }

    return app
