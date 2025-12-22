# app/__init__.py
from __future__ import annotations

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app.extensions import db

# Si usás Flask-Migrate, dejalo. Si no lo usás, podés borrar migrate.
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
    # Blueprints
    # -------------------------
    # main blueprint (tu routes.py debe exponer main_bp)
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # coach blueprint (tu carpeta app/blueprints)
    # IMPORTANTE: acá asumimos que app/blueprints/__init__.py expone "bp"
    try:
        from app.blueprints import bp as coach_bp
        app.register_blueprint(coach_bp)
    except Exception:
        # si todavía no existe o no está listo, no rompe el arranque
        pass

    # strava blueprint (si existe)
    try:
        from app.strava import strava_bp
        app.register_blueprint(strava_bp)
    except Exception:
        pass

    # -------------------------
    # Contexto global para templates (admin_ok)
    # -------------------------
    from flask_login import current_user

    @app.context_processor
    def inject_admin_ok():
        admin_ok = False
        try:
            admin_ok = bool(getattr(current_user, "is_authenticated", False) and getattr(current_user, "is_admin", False))
        except Exception:
            admin_ok = False
        return {"admin_ok": admin_ok}

    return app
