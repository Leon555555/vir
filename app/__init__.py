import os
import datetime

from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import db, migrate
from app.models import User  # ✅ mantenelo simple


def create_app():
    app = Flask(__name__)

    # =========================
    # CONFIG BASE
    # =========================
    # ⚠️ En Render: poné SECRET_KEY en Environment Variables (una clave larga)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-ultra-segura")

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # =========================
    # FIX HTTPS + COOKIES (Render)
    # =========================
    # Render está detrás de un proxy HTTPS. Esto hace que Flask "vea" el esquema correcto.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Detectar entorno (Render setea RENDER=1 normalmente)
    is_prod = os.getenv("RENDER") == "1" or os.getenv("FLASK_ENV") == "production"

    # Cookies seguras: en producción SIEMPRE
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # En Render es HTTPS → Secure True
    # (si lo ponés True sin ProxyFix, se rompe)
    app.config["SESSION_COOKIE_SECURE"] = True if is_prod else False

    # (Opcional, pero ayuda a que los redirects generen https)
    app.config["PREFERRED_URL_SCHEME"] = "https" if is_prod else "http"

    # =========================
    # INIT EXTENSIONS
    # =========================
    db.init_app(app)
    migrate.init_app(app, db)

    # =========================
    # LOGIN
    # =========================
    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # =========================
    # CONTEXT
    # =========================
    @app.context_processor
    def inject_datetime():
        return {"datetime_now": datetime.datetime.utcnow}

    # =========================
    # ROUTES / BLUEPRINT
    # =========================
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # =========================
    # DB INIT (OK para tu caso)
    # =========================
    with app.app_context():
        db.create_all()
        print("✅ Tablas verificadas correctamente.")

    return app
