# app/__init__.py
import os
import datetime

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import db, migrate, login_manager
from app.models import User


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-ultra-segura")

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Render proxy / https
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    is_prod = os.getenv("RENDER") == "1" or os.getenv("FLASK_ENV") == "production"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = True if is_prod else False
    app.config["PREFERRED_URL_SCHEME"] = "https" if is_prod else "http"

    db.init_app(app)
    migrate.init_app(app, db)

    # ✅ un solo LoginManager (el de extensions.py)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    @app.context_processor
    def inject_datetime():
        return {"datetime_now": datetime.datetime.utcnow}

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        print("✅ Tablas verificadas correctamente.")

    return app
