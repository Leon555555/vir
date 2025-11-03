import os
import datetime
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text
from app.extensions import db, migrate
from app.models import User, Rutina, DiaPlan  # ✅ limpio, sin RutinaItem

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-ultra-segura")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    @app.context_processor
    def inject_datetime():
        return {"datetime_now": datetime.datetime.utcnow}

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        print("✅ Tablas verificadas correctamente.")

    return app
