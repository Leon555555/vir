# app/__init__.py
from __future__ import annotations

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app.extensions import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("Falta DATABASE_URL o SQLALCHEMY_DATABASE_URI en variables de entorno.")

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"  # tu login vive en blueprint main
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ✅ Registrar blueprint principal
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # ✅ Registrar blueprint strava (para url_for('strava.connect'))
    from app.blueprints.strava import strava_bp
    app.register_blueprint(strava_bp, url_prefix="/strava")

    return app
