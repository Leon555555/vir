from flask import Flask
from flask_login import LoginManager
from app.extensions import db
from app.models import User
from datetime import datetime


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "clave-ultra-segura"

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow}

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # =========================================================
    # 👑 Crear automáticamente el usuario admin si no existe
    # =========================================================
    with app.app_context():
        db.create_all()
        email_admin = "viru@vir.app"
        password_admin = "Viru12345!"
        nombre_admin = "Viru"

        admin = User.query.filter_by(email=email_admin).first()
        if not admin:
            print("🟢 Creando usuario administrador ViR...")
            admin = User(nombre=nombre_admin, email=email_admin)
            admin.set_password(password_admin)
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin creado: {email_admin} / {password_admin}")
        else:
            print("🔹 Usuario admin ya existe, no se crea nuevamente.")

    return app
