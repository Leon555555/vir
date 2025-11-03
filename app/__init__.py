import os
import datetime
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text
from app.extensions import db, migrate
from app.models import User, Rutina, Ejercicio, DiaPlan



def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-ultra-segura")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Configurar login
    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    # ✅ Inyección de fecha para el footer
    @app.context_processor
    def inject_datetime():
        return {"datetime_now": datetime.datetime.utcnow}

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # ===============================
    # CREAR TABLAS SI NO EXISTEN
    # ===============================
    with app.app_context():
        db.create_all()

        # Crear tablas manualmente si faltan
        try:
            db.session.execute(text("SELECT id FROM rutina LIMIT 1;"))
        except Exception:
            print("⚙️ Creando tablas rutina y rutina_item manualmente...")
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS rutina (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(120) NOT NULL,
                    descripcion TEXT,
                    created_by INTEGER REFERENCES "user"(id)
                );
                """)
            )
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS rutina_item (
                    id SERIAL PRIMARY KEY,
                    rutina_id INTEGER REFERENCES rutina(id),
                    orden INTEGER DEFAULT 0,
                    nombre VARCHAR(120) NOT NULL,
                    reps VARCHAR(80),
                    video_url VARCHAR(255),
                    imagen_url VARCHAR(255),
                    nota TEXT
                );
                """)
            )
            db.session.commit()
            print("✅ Tablas rutina y rutina_item creadas correctamente.")

        print("✅ Tablas verificadas correctamente.")

    return app
