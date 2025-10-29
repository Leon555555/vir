from flask import Flask
from app.extensions import db, migrate, login_manager
from app.models import User


def create_app():
    app = Flask(__name__)

    # =============================
    # 🔐 CONFIGURACIÓN BÁSICA
    # =============================
    app.config["SECRET_KEY"] = "clave-ultra-segura"
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # =============================
    # 🔧 INICIALIZAR EXTENSIONES
    # =============================
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # =============================
    # 👤 CARGADOR DE USUARIO
    # =============================
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # =============================
    # 🔗 REGISTRAR BLUEPRINTS
    # =============================
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
