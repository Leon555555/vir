import os
import datetime
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text
from app.extensions import db, migrate
from app.models import User, Rutina, RutinaItem, DiaPlan


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

    # ✅ inyección de fecha para el footer
    @app.context_processor
    def inject_datetime():
        return {"datetime_now": datetime.datetime.utcnow}

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # ===============================
    # CREAR TABLAS AUTOMÁTICAMENTE
    # ===============================
    with app.app_context():
        # 🔥 Limpieza de tablas mal creadas (soluciona "nombre no existe")
        db.session.execute(text("DROP TABLE IF EXISTS rutina CASCADE;"))
        db.session.execute(text("DROP TABLE IF EXISTS rutina_item CASCADE;"))
        db.session.commit()

        db.create_all()

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

        # Crear admin si no existe
        admin = User.query.filter_by(email="admin@vir.app").first()
        if not admin:
            admin = User(nombre="Admin ViR", email="admin@vir.app", grupo="Entrenador")
            admin.set_password("vir2025")
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin creado: admin@vir.app / vir2025")
        else:
            print("✅ Admin ya existe.")

        # Crear atleta de prueba si no existe
        viru = User.query.filter_by(email="viru@vir.app").first()
        if not viru:
            viru = User(nombre="Viru", email="viru@vir.app", grupo="Atleta")
            viru.set_password("viru2025")
            db.session.add(viru)
            db.session.commit()
            print("✅ Usuario 'Viru' creado: viru@vir.app / viru2025")
        else:
            print("✅ Usuario 'Viru' ya existe.")

    return app
