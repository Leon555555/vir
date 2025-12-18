# app/__init__.py
import os
import datetime

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import db, migrate, login_manager
from app.models import User

# ✅ IMPORTANTE: registrar modelos Strava (si existe el archivo).
# Esto hace que SQLAlchemy "vea" IntegrationAccount / ExternalActivity
# y que create_all los cree cuando AUTO_CREATE_DB=1.
try:
    import app.models_strava  # noqa: F401
    print("✅ models_strava importado (modelos Strava registrados).")
except Exception as e:
    print(f"ℹ️ models_strava no importado todavía: {e}")


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-ultra-segura")

    # Si tu DATABASE_URL viene de Render, úsala tal cual.
    # Recomendado: en Render setear DATABASE_URL con ?sslmode=require
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

    # Blueprints existentes
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # ✅ Blueprint Strava (si existe el archivo). No toca routes.py
    try:
        from app.blueprints.strava_bp import strava_bp
        app.register_blueprint(strava_bp)
        print("✅ Strava blueprint registrado.")
    except Exception as e:
        # No rompemos el arranque si todavía no agregaste los archivos de Strava
        print(f"ℹ️ Strava blueprint no registrado todavía: {e}")

    # ❗ NO crear tablas en cada arranque en producción.
    # En Render esto puede tumbar el servicio si la DB está reiniciando o corta SSL.
    # Usá AUTO_CREATE_DB=1 solo cuando quieras forzar create_all (una vez).
    with app.app_context():
        if os.getenv("AUTO_CREATE_DB", "0") == "1":
            try:
                db.create_all()
                print("✅ Tablas verificadas/creadas (AUTO_CREATE_DB=1).")
            except Exception as e:
                print(f"⚠️ No se pudo ejecutar create_all: {e}")
        else:
            print("ℹ️ AUTO_CREATE_DB=0: no se ejecuta db.create_all() en el arranque.")

    return app
